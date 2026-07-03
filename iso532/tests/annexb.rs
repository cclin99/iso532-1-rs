mod common;
use common::*;
use iso532::{loudness_zwst, FieldType};

/// ISO 532-1 section 5.1 compliance: within 5% relative or 0.1 absolute,
/// same criterion as mosqito's tests (isclose rtol=0.05, atol=0.1).
fn isoclose(got: &[f64], want: &[f64]) -> bool {
    got.iter()
        .zip(want)
        .all(|(g, w)| (g - w).abs() <= 0.1 + 0.05 * w.abs())
}

fn annexb_csv(file: &str) -> Vec<f64> {
    let path = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .join("data/annexb")
        .join(file);
    let txt = std::fs::read_to_string(&path)
        .unwrap_or_else(|e| panic!("missing {path:?} (run tools/setup_env.sh): {e}"));
    txt.lines()
        .skip(1)
        .filter_map(|line| line.trim().parse().ok())
        .collect()
}

#[test]
fn annexb_stationary_signal3_1khz_60db() {
    let sig = read_bin("annexb_sig3", "sig.bin");
    let want_spec = annexb_csv("test_signal_3.csv");
    assert_eq!(want_spec.len(), 240);
    let r = loudness_zwst(&sig, 48000.0, FieldType::Free).unwrap();
    assert!(isoclose(&[r.n], &[4.019]), "N = {}", r.n);
    assert!(isoclose(&r.n_specific, &want_spec));
}

#[test]
fn annexb_stationary_signal5_pinknoise_60db() {
    let sig = read_bin("annexb_sig5", "sig.bin");
    let want_spec = annexb_csv("test_signal_5.csv");
    assert_eq!(want_spec.len(), 240);
    let r = loudness_zwst(&sig, 48000.0, FieldType::Free).unwrap();
    assert!(isoclose(&[r.n], &[10.498]), "N = {}", r.n);
    assert!(isoclose(&r.n_specific, &want_spec));
}
