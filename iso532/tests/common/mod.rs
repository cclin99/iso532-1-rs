use std::path::{Path, PathBuf};

pub mod annexb_check;

#[allow(dead_code)]
const FS: f64 = 48_000.0;

#[allow(dead_code)]
pub fn synth_signal() -> Vec<f64> {
    (0..48_000)
        .map(|i| {
            let t = i as f64 / FS;
            0.25 * (2.0 * std::f64::consts::PI * 440.0 * t).sin()
                + 0.10 * (2.0 * std::f64::consts::PI * 1_760.0 * t).sin()
                + 0.04 * (2.0 * std::f64::consts::PI * 6_400.0 * t).sin()
        })
        .collect()
}

#[allow(dead_code)]
pub fn run_chunked(
    signal: &[f64],
    chunks: impl Iterator<Item = usize>,
) -> Vec<iso532::StreamFrame> {
    let mut stream = iso532::ZwtvStream::new(iso532::FieldType::Free);
    let mut out = vec![
        iso532::StreamFrame::default();
        iso532::ZwtvStream::max_frames_for_chunk(signal.len())
    ];
    let mut got = Vec::new();
    let mut pos = 0;
    for size in chunks.chain(std::iter::repeat(480)) {
        if pos >= signal.len() {
            break;
        }
        let end = (pos + size).min(signal.len());
        let n = stream.push(&signal[pos..end], &mut out);
        got.extend_from_slice(&out[..n]);
        pos = end;
    }
    let n = stream.flush(&mut out);
    got.extend_from_slice(&out[..n]);
    got
}

#[allow(dead_code)]
pub fn synth_core(n_time: usize) -> Vec<f64> {
    let mut core = vec![0.0; 21 * n_time];
    for band in 0..21 {
        for t in 0..n_time {
            let phase = (t as f64 / 40.0 + band as f64).sin();
            core[band * n_time + t] = (phase * 0.6 + 0.5).max(0.0);
        }
    }
    core
}

#[allow(dead_code)]
pub fn golden_dir(name: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .join("data/golden")
        .join(name)
}

#[allow(dead_code)]
pub fn read_bin(name: &str, file: &str) -> Vec<f64> {
    read_bin_path(&golden_dir(name).join(file))
}

/// Little-endian f64 reader. The file must be a whole number of 8-byte words;
/// any trailing bytes are a hard failure (not truncated silently).
#[allow(dead_code)]
pub fn read_bin_path(path: &Path) -> Vec<f64> {
    let bytes = std::fs::read(path)
        .unwrap_or_else(|e| panic!("missing golden {path:?} (run tools/gen_golden.py): {e}"));
    let (words, rest) = bytes.as_chunks::<8>();
    assert!(
        rest.is_empty(),
        "golden {path:?}: {} trailing bytes, not a whole number of f64",
        rest.len()
    );
    words.iter().map(|c| f64::from_le_bytes(*c)).collect()
}

#[allow(dead_code)]
pub fn assert_close(got: &[f64], want: &[f64], rtol: f64, atol: f64, ctx: &str) {
    assert_eq!(got.len(), want.len(), "{ctx}: length mismatch");
    for (i, (g, w)) in got.iter().zip(want).enumerate() {
        let tol = atol + rtol * w.abs();
        assert!(
            (g - w).abs() <= tol,
            "{ctx}[{i}]: got {g:e}, want {w:e}, |diff|={:e} > tol {tol:e}",
            (g - w).abs()
        );
    }
}
/// Record-only comparison (0.4.0 D-H, MoSQITo specific loudness): checks the
/// lengths and that both sides are finite, prints the maximum |got - want| and
/// returns it. Not a gate.
#[allow(dead_code)]
pub fn record_max_abs_diff(got: &[f64], want: &[f64], ctx: &str) -> f64 {
    assert_eq!(got.len(), want.len(), "{ctx}: length mismatch");
    assert!(!want.is_empty(), "{ctx}: empty reference");
    let mut worst = (0.0_f64, 0usize);
    for (i, (g, w)) in got.iter().zip(want).enumerate() {
        assert!(g.is_finite(), "{ctx}[{i}]: result not finite: {g}");
        assert!(w.is_finite(), "{ctx}[{i}]: reference not finite: {w}");
        let d = (g - w).abs();
        if d > worst.0 {
            worst = (d, i);
        }
    }
    eprintln!(
        "{ctx}: max |diff| {:.3e} at index {} (recorded, not gated)",
        worst.0, worst.1
    );
    worst.0
}

#[allow(dead_code)]
pub fn fnv1a_f64(values: &[f64]) -> u64 {
    let mut hash = 0xcbf2_9ce4_8422_2325_u64;
    for value in values {
        for byte in value.to_le_bytes() {
            hash ^= u64::from(byte);
            hash = hash.wrapping_mul(0x0000_0100_0000_01b3);
        }
    }
    hash
}
/// Returns true when AVX2 is available. When it is not: fails hard if the
/// REQUIRE_AVX2 env var is set (CI anti-silent-skip gate), otherwise logs
/// and returns false so the caller can skip.
#[allow(dead_code)]
pub fn require_avx2_or_skip(ctx: &str) -> bool {
    if iso532::simd::avx2_available() {
        return true;
    }
    assert!(
        std::env::var_os("REQUIRE_AVX2").is_none(),
        "{ctx}: REQUIRE_AVX2 is set but AVX2 is unavailable on this runner"
    );
    eprintln!("{ctx}: AVX2 not available; skipping");
    false
}
