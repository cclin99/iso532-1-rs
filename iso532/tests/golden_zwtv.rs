mod common;
use common::*;
use iso532::zwtv::nonlinear_decay::nl_loudness_scalar;
use iso532::zwtv::temporal_weighting::temporal_weighting;
use iso532::zwtv::third_octave_levels::third_octave_levels_scalar;
use iso532::{loudness_zwtv, FieldType};

#[test]
fn third_octave_levels_matches_mosqito() {
    for sig in ["sine_1k_60", "pulse_1k_70", "step_60_80", "white_60"] {
        let x = read_bin(sig, "sig.bin");
        let want = read_bin(sig, "third_octave_level.bin");
        let (got, n_time) = third_octave_levels_scalar(&x);
        assert_eq!(n_time, want.len() / 28, "{sig}: n_time");
        assert_close(
            &got,
            &want,
            1e-7,
            1e-12,
            &format!("{sig}/third_octave_level"),
        );
    }
}

#[test]
fn nl_loudness_matches_mosqito() {
    for sig in ["sine_1k_60", "pulse_1k_70", "step_60_80", "white_60"] {
        let core = read_bin(sig, "core_loudness.bin");
        let want = read_bin(sig, "nl_loudness.bin");
        let n_time = core.len() / 21;
        let got = nl_loudness_scalar(&core, n_time);
        assert_close(&got, &want, 1e-6, 1e-9, &format!("{sig}/nl_loudness"));
    }
}

#[test]
fn temporal_weighting_matches_mosqito() {
    for sig in ["pulse_1k_70", "step_60_80", "white_60"] {
        let loud = read_bin(sig, "loudness_raw.bin");
        let want = read_bin(sig, "filt_loudness.bin");
        let got = temporal_weighting(&loud);
        assert_close(&got, &want, 1e-9, 1e-12, &format!("{sig}/temporal"));
    }
}

#[test]
fn zwtv_end_to_end_matches_mosqito() {
    for sig in ["sine_1k_60", "pulse_1k_70", "step_60_80", "annexb_sig10"] {
        let x = read_bin(sig, "sig.bin");
        let want_n = read_bin(sig, "N_time.bin");
        let want_spec = read_bin(sig, "N_spec_time.bin");
        let r = loudness_zwtv(&x, 48000.0, FieldType::Free).unwrap();
        assert_eq!(r.bark_axis.len(), 240, "{sig}: bark axis");
        assert_close(&r.n, &want_n, 1e-6, 1e-9, &format!("{sig}/N_time"));
        assert_close(
            &r.n_specific,
            &want_spec,
            1e-6,
            1e-9,
            &format!("{sig}/N_spec_time"),
        );
    }
}
/// Bitwise output snapshot recorded after R4 (commit e96dffa) on the AVX2
/// auto-dispatch path. Rayon/Sequential are bitwise-equal (see determinism
/// tests), so these values do not depend on thread count. Regenerate with
/// `cargo test --test golden_zwtv dump_zwtv_output_hashes -- --ignored --nocapture`.
const R4_SNAPSHOT_AVX2: [(&str, u64, u64, u64); 4] = [
    (
        "sine_1k_60",
        0x0b10971021634b4e,
        0x62496b610f7c223d,
        0xf076bcb342595537,
    ),
    (
        "pulse_1k_70",
        0xb92a2b970de3067f,
        0xbdab430b961720f0,
        0xf076bcb342595537,
    ),
    (
        "step_60_80",
        0x40ac75b0dcaed5a8,
        0x2fdc839b4f702621,
        0xf076bcb342595537,
    ),
    (
        "annexb_sig10",
        0x83da1e1c06d5296c,
        0x3c2b914686402b54,
        0xf076bcb342595537,
    ),
];

#[test]
fn zwtv_output_hashes_match_r4_snapshot() {
    if !require_avx2_or_skip("zwtv_output_hashes_match_r4_snapshot") {
        return;
    }
    for (sig, want_n, want_spec, want_time) in R4_SNAPSHOT_AVX2 {
        let x = read_bin(sig, "sig.bin");
        let r = loudness_zwtv(&x, 48000.0, FieldType::Free).unwrap();
        assert_eq!(fnv1a_f64(&r.n), want_n, "{sig}: N hash drifted");
        assert_eq!(
            fnv1a_f64(&r.n_specific),
            want_spec,
            "{sig}: N_specific hash drifted"
        );
        assert_eq!(
            fnv1a_f64(&r.time_axis),
            want_time,
            "{sig}: time hash drifted"
        );
    }
}

#[test]
#[ignore = "manual helper: bitwise output snapshot for refactor verification"]
fn dump_zwtv_output_hashes() {
    for sig in ["sine_1k_60", "pulse_1k_70", "step_60_80", "annexb_sig10"] {
        let x = read_bin(sig, "sig.bin");
        let r = loudness_zwtv(&x, 48000.0, FieldType::Free).unwrap();
        println!(
            "{sig}: n={:016x} spec={:016x} time={:016x}",
            fnv1a_f64(&r.n),
            fnv1a_f64(&r.n_specific),
            fnv1a_f64(&r.time_axis),
        );
    }
}
