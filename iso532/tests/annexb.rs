mod common;
use common::annexb_check::{annexb_csv, annexb_verdict, Verdict};
use common::*;
use iso532::{loudness_zwst, loudness_zwtv, FieldType};

/// ISO 532-1 Annex B acceptance per point: `|got - ref| <= max(0.1, 0.05 * |ref|)`,
/// the rule of the official Annex B workbook (V-01, `docs/修正報告2.md` §11.5).
/// Fail-closed: invalid data (empty, length mismatch, NaN/Inf, negative
/// reference) is reported as `Invalid`, never as a pass. Strict 0 exceptions.
fn assert_annexb(got: &[f64], reference: &[f64], ctx: &str) {
    let verdict = annexb_verdict(got, reference);
    assert!(
        matches!(verdict, Verdict::Pass { .. }),
        "{ctx}: Annex B verdict {verdict:?}"
    );
}

#[test]
fn annexb_stationary_signal3_1khz_60db() {
    let sig = read_bin("annexb_sig3", "sig.bin");
    let want_spec = annexb_csv("test_signal_3.csv");
    assert_eq!(want_spec.len(), 240);
    let r = loudness_zwst(&sig, 48000.0, FieldType::Free).unwrap();
    assert_annexb(&[r.n], &[4.019], "sig3 N");
    assert_annexb(&r.n_specific, &want_spec, "sig3 N_specific vs ISO csv");
}

#[test]
fn annexb_stationary_signal5_pinknoise_60db() {
    let sig = read_bin("annexb_sig5", "sig.bin");
    let want_spec = annexb_csv("test_signal_5.csv");
    assert_eq!(want_spec.len(), 240);
    let r = loudness_zwst(&sig, 48000.0, FieldType::Free).unwrap();
    assert_annexb(&[r.n], &[10.498], "sig5 N");
    assert_annexb(&r.n_specific, &want_spec, "sig5 N_specific vs ISO csv");
}

#[test]
fn annexb_timevarying_signal10() {
    let sig = read_bin("annexb_sig10", "sig.bin");
    let want_n = read_bin("annexb_sig10", "N_time.bin");
    let iso_time = read_bin("annexb_sig10", "tv_time.bin");
    let iso_ref = read_bin("annexb_sig10", "tv_nref.bin");
    let r = loudness_zwtv(&sig, 48000.0, FieldType::Free).unwrap();
    // Compatibility comparison with the MoSQITo 1.2.1 golden only (D-E of the
    // 0.4.0 phase plan): since 0.4.0 the slope stage follows Annex A (F-04/F-05)
    // and MoSQITo is no longer the acceptance reference, so the bound is the
    // 5e-3 sone compatibility tolerance. The Annex B verdicts below are the
    // conformance check and keep their rule unchanged.
    assert_close(
        &r.n,
        &want_n,
        0.0,
        5e-3,
        "sig10 N(t) vs mosqito (compatibility)",
    );
    assert_close(
        &r.time_axis,
        &iso_time,
        1e-12,
        1e-12,
        "sig10 time axis vs ISO xlsx",
    );
    // `annexb_verdict` also rejects a negative or non-finite `tv_nref.bin`
    // (Invalid), which would be a fixture finding rather than a numeric failure.
    assert_annexb(&r.n, &iso_ref, "sig10 N(t) vs ISO xlsx reference");
}
