use std::path::PathBuf;

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
    let path = golden_dir(name).join(file);
    let bytes = std::fs::read(&path)
        .unwrap_or_else(|e| panic!("missing golden {path:?} (run tools/gen_golden.py): {e}"));
    bytes
        .chunks_exact(8)
        .map(|c| f64::from_le_bytes(c.try_into().unwrap()))
        .collect()
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
