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
