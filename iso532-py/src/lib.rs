//! Python bindings for the `iso532` crate. The input is copied to an owned buffer
//! before the GIL is released (soundness: other Python threads may mutate
//! the ndarray mid-computation); outputs are moved into numpy arrays
//! without an extra copy.

use numpy::ndarray::Array2;
use numpy::{IntoPyArray, PyArray1, PyArray2, PyReadonlyArray1};
use pyo3::exceptions::{PyRuntimeError, PyTypeError, PyValueError};
use pyo3::prelude::*;

type ZwtvOutput<'py> = (
    Bound<'py, PyArray1<f64>>,
    Bound<'py, PyArray2<f64>>,
    Bound<'py, PyArray1<f64>>,
    Bound<'py, PyArray1<f64>>,
);
type ZwstOutput<'py> = (f64, Bound<'py, PyArray1<f64>>, Bound<'py, PyArray1<f64>>);
type StreamOutput<'py> = (
    Bound<'py, PyArray1<f64>>,
    Bound<'py, PyArray1<f64>>,
    Bound<'py, PyArray1<u64>>,
    Bound<'py, PyArray1<u32>>,
);

fn frames_to_arrays<'py>(
    py: Python<'py>,
    frames: &[iso532_core::StreamFrame],
) -> StreamOutput<'py> {
    let n: Vec<f64> = frames.iter().map(|f| f.n).collect();
    let n_phon: Vec<f64> = frames.iter().map(|f| f.n_phon).collect();
    let t = frames.iter().map(|f| f.t_frame_index).collect::<Vec<_>>();
    let flags = frames.iter().map(|f| f.flags.bits()).collect::<Vec<_>>();
    (
        n.into_pyarray(py),
        n_phon.into_pyarray(py),
        t.into_pyarray(py),
        flags.into_pyarray(py),
    )
}

fn parse_field(s: &str) -> PyResult<iso532_core::FieldType> {
    s.parse().map_err(|_| {
        PyValueError::new_err(format!(
            "field_type must be \"free\" or \"diffuse\", got {s:?}"
        ))
    })
}

fn contiguous<'py, 'a>(signal: &'a PyReadonlyArray1<'py, f64>) -> PyResult<&'a [f64]> {
    signal
        .as_slice()
        .map_err(|_| PyTypeError::new_err("signal must be a C-contiguous 1-D float64 ndarray"))
}

/// Time-varying loudness (ISO 532-1 zwtv).
/// Returns (n[frames], n_specific[240, frames], bark_axis[240], time_axis[frames]).
#[pyfunction]
#[pyo3(signature = (signal, fs, field_type = "free"))]
fn loudness_zwtv<'py>(
    py: Python<'py>,
    signal: PyReadonlyArray1<'py, f64>,
    fs: f64,
    field_type: &str,
) -> PyResult<ZwtvOutput<'py>> {
    let field = parse_field(field_type)?;
    let owned = contiguous(&signal)?.to_vec();
    let r = py
        .allow_threads(move || iso532_core::loudness_zwtv(&owned, fs, field))
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
    let frames = r.n.len();
    let spec = Array2::from_shape_vec((240, frames), r.n_specific)
        .expect("n_specific is 240*frames by construction")
        .into_pyarray(py);
    Ok((
        r.n.into_pyarray(py),
        spec,
        r.bark_axis.into_pyarray(py),
        r.time_axis.into_pyarray(py),
    ))
}

/// Stationary loudness (ISO 532-1 zwst).
/// Returns (n, n_specific[240], bark_axis[240]).
#[pyfunction]
#[pyo3(signature = (signal, fs, field_type = "free"))]
fn loudness_zwst<'py>(
    py: Python<'py>,
    signal: PyReadonlyArray1<'py, f64>,
    fs: f64,
    field_type: &str,
) -> PyResult<ZwstOutput<'py>> {
    let field = parse_field(field_type)?;
    let owned = contiguous(&signal)?.to_vec();
    let r = py
        .allow_threads(move || iso532_core::loudness_zwst(&owned, fs, field))
        .map_err(|e| PyValueError::new_err(e.to_string()))?;
    Ok((
        r.n,
        r.n_specific.into_pyarray(py),
        r.bark_axis.into_pyarray(py),
    ))
}

/// Convert loudness in sone to loudness level in phon using the frozen R5 formula.
#[pyfunction]
fn sone2phon(n: f64) -> PyResult<f64> {
    if !n.is_finite() || n < 0.0 {
        return Err(PyValueError::new_err("sone must be non-negative"));
    }
    Ok(iso532_core::sone2phon(n))
}

/// Streaming time-varying loudness (ISO 532-1 zwtv), 48 kHz, 24-sample latency.
///
/// Single-threaded use only (the handle has no internal lock). Unlike the batch
/// API, non-finite samples do not raise: they are zeroed and reported via the
/// NONFINITE_INPUT flag on the frame that consumes them, or via `residual_flags`
/// after `flush()` if no frame follows. Before `flush()`, `residual_flags` is
/// provisional (pending flags travel with the next output frame). `push()` after
/// `flush()` raises RuntimeError; call `reset()` to reuse the stream. Each call
/// allocates fresh output arrays (the zero-allocation guarantee is a Rust-core
/// hot-path contract, not a binding-level one).
#[pyclass(name = "ZwtvStream", unsendable)]
struct PyZwtvStream {
    // Boxed on purpose: the core stream is align(32) (inline AVX2 __m256d
    // constants), but Python object allocation only guarantees 16-byte
    // alignment. Storing it inline in the pyclass is UB and faults on
    // aligned SIMD loads whenever the object lands on a 16-mod-32 address.
    inner: Box<iso532_core::ZwtvStream>,
    scratch: Vec<iso532_core::StreamFrame>,
    flushed: bool,
}

#[pymethods]
impl PyZwtvStream {
    #[new]
    #[pyo3(signature = (field_type = "free"))]
    fn new(field_type: &str) -> PyResult<Self> {
        Ok(Self {
            inner: Box::new(iso532_core::ZwtvStream::new(parse_field(field_type)?)),
            scratch: Vec::new(),
            flushed: false,
        })
    }

    /// Push a chunk; returns (n, n_phon, t_frame_index, flags) for completed frames.
    fn push<'py>(
        &mut self,
        py: Python<'py>,
        chunk: PyReadonlyArray1<'py, f64>,
    ) -> PyResult<StreamOutput<'py>> {
        if self.flushed {
            return Err(PyRuntimeError::new_err(
                "stream is flushed; call reset() before pushing again",
            ));
        }
        let owned = contiguous(&chunk)?.to_vec();
        let cap = iso532_core::ZwtvStream::max_frames_for_chunk(owned.len());
        self.scratch.resize(cap.max(1), Default::default());
        let (inner, scratch) = (&mut self.inner, &mut self.scratch[..]);
        let written = py.allow_threads(move || inner.push(&owned, scratch));
        Ok(frames_to_arrays(py, &self.scratch[..written]))
    }

    /// Drain the held tail frame. Idempotent: repeated flushes return empty arrays.
    fn flush<'py>(&mut self, py: Python<'py>) -> StreamOutput<'py> {
        self.scratch.resize(1, Default::default());
        let (inner, scratch) = (&mut self.inner, &mut self.scratch[..]);
        let written = py.allow_threads(move || inner.flush(scratch));
        self.flushed = true;
        frames_to_arrays(py, &self.scratch[..written])
    }

    /// Reset to a freshly-constructed stream (bitwise-equivalent output).
    fn reset(&mut self) {
        self.inner.reset();
        self.flushed = false;
    }

    /// Undelivered flag bits (provisional before `flush()`).
    #[getter]
    fn residual_flags(&self) -> u32 {
        self.inner.residual_flags().bits()
    }

    #[staticmethod]
    fn latency_samples() -> usize {
        iso532_core::ZwtvStream::latency_samples()
    }

    #[staticmethod]
    fn max_frames_for_chunk(chunk_len: usize) -> usize {
        iso532_core::ZwtvStream::max_frames_for_chunk(chunk_len)
    }
}

#[pymodule]
fn iso532(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(loudness_zwtv, m)?)?;
    m.add_function(wrap_pyfunction!(loudness_zwst, m)?)?;
    m.add_function(wrap_pyfunction!(sone2phon, m)?)?;
    m.add_class::<PyZwtvStream>()?;
    m.add("N_WARMUP_FRAMES", iso532_core::N_WARMUP_FRAMES)?;
    m.add(
        "FLAG_CLAMPED_120DB",
        iso532_core::FrameFlags::CLAMPED_120DB.bits(),
    )?;
    m.add(
        "FLAG_NONFINITE_INPUT",
        iso532_core::FrameFlags::NONFINITE_INPUT.bits(),
    )?;
    m.add("FLAG_WARMUP", iso532_core::FrameFlags::WARMUP.bits())?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
