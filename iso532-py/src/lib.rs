//! Python bindings for the `iso532` crate. Batch API only (R3); the
//! streaming API arrives with R5. The input is copied to an owned buffer
//! before the GIL is released (soundness: other Python threads may mutate
//! the ndarray mid-computation); outputs are moved into numpy arrays
//! without an extra copy.

use numpy::ndarray::Array2;
use numpy::{IntoPyArray, PyArray1, PyArray2, PyReadonlyArray1};
use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;

type ZwtvOutput<'py> = (
    Bound<'py, PyArray1<f64>>,
    Bound<'py, PyArray2<f64>>,
    Bound<'py, PyArray1<f64>>,
    Bound<'py, PyArray1<f64>>,
);
type ZwstOutput<'py> = (f64, Bound<'py, PyArray1<f64>>, Bound<'py, PyArray1<f64>>);
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
fn sone2phon(n: f64) -> f64 {
    iso532_core::sone2phon(n)
}

#[pymodule]
fn iso532(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(loudness_zwtv, m)?)?;
    m.add_function(wrap_pyfunction!(loudness_zwst, m)?)?;
    m.add_function(wrap_pyfunction!(sone2phon, m)?)?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
