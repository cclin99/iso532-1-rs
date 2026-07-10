use std::path::PathBuf;

pub fn golden_dir(name: &str) -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .join("data/golden")
        .join(name)
}

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
