//! MoSQITo 1.2.1 goldens. The stage tests (third-octave levels, nonlinear
//! decay, temporal weighting) stay tight. Since 0.4.0 the slope stage follows
//! ISO 532-1 Annex A (F-04 no per-frame rounding, F-05 band completion) and the
//! correctness reference is the Annex A C golden (`tests/golden_c.rs`); the
//! end-to-end N(t) comparisons below are a compatibility check against MoSQITo
//! (相容性對照) with the D-E bound of 5e-3 sone (phase plan 0.4.0). N'(t) is
//! recorded, not gated, against MoSQITo since F-07 (D-H): Annex A writes the
//! core loudness (or the containing segment) in the cell where a slope ends,
//! MoSQITo extrapolates the slope there (up to ~4e-2 sone/Bark).

mod common;
use common::*;
use iso532::zwtv::nonlinear_decay::{nl_loudness_scalar, nl_loudness_scalar_with};
use iso532::zwtv::temporal_weighting::temporal_weighting;
use iso532::zwtv::third_octave_levels::third_octave_levels_scalar;
use iso532::zwtv::NlInit;
use iso532::{loudness_zwtv, FieldType, ZwtvProcessor};

// MoSQITo 1.2.1 seeds the nonlinear decay from the last frame (F-02); the
// golden fixtures therefore compare exactly only under `NlInit::MosqitoTail`.
// Fixtures whose signal ends in silence have a zero seed and are identical
// under both initialisations.
const SILENT_TAIL: [&str; 2] = ["pulse_1k_70", "annexb_sig10"];

/// MoSQITo compatibility bound for the total loudness (D-E, D-H), sone.
const COMPAT_TOL: f64 = 5e-3;

fn mosqito_compatible(sig: &[f64]) -> iso532::LoudnessTimeVarying {
    ZwtvProcessor::new()
        .process_with(sig, 48000.0, FieldType::Free, NlInit::MosqitoTail)
        .unwrap()
}

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
fn nl_loudness_matches_mosqito_under_tail_init() {
    for sig in ["sine_1k_60", "pulse_1k_70", "step_60_80", "white_60"] {
        let core = read_bin(sig, "core_loudness.bin");
        let want = read_bin(sig, "nl_loudness.bin");
        let n_time = core.len() / 21;
        let got = nl_loudness_scalar_with(&core, n_time, NlInit::MosqitoTail);
        assert_close(&got, &want, 1e-6, 1e-9, &format!("{sig}/nl_loudness"));
    }
}

#[test]
fn nl_loudness_zero_init_equals_golden_when_the_fixture_ends_in_silence() {
    for sig in SILENT_TAIL {
        let core = read_bin(sig, "core_loudness.bin");
        let n_time = core.len() / 21;
        let last_frame_max = (0..21)
            .map(|b| core[b * n_time + n_time - 1])
            .fold(0.0, f64::max);
        assert_eq!(last_frame_max, 0.0, "{sig}: fixture must end in silence");
        let zero = nl_loudness_scalar(&core, n_time);
        let tail = nl_loudness_scalar_with(&core, n_time, NlInit::MosqitoTail);
        assert_eq!(
            zero, tail,
            "{sig}: zero seed must make both paths identical"
        );
        let want = read_bin(sig, "nl_loudness.bin");
        assert_close(&zero, &want, 1e-6, 1e-9, &format!("{sig}/nl_loudness zero"));
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
fn zwtv_end_to_end_compat_mosqito_under_tail_init() {
    for sig in ["sine_1k_60", "pulse_1k_70", "step_60_80", "annexb_sig10"] {
        let x = read_bin(sig, "sig.bin");
        let want_n = read_bin(sig, "N_time.bin");
        let want_spec = read_bin(sig, "N_spec_time.bin");
        let r = mosqito_compatible(&x);
        assert_eq!(r.bark_axis.len(), 240, "{sig}: bark axis");
        assert_close(
            &r.n,
            &want_n,
            0.0,
            COMPAT_TOL,
            &format!("{sig}/N_time (compatibility)"),
        );
        record_max_abs_diff(
            &r.n_specific,
            &want_spec,
            &format!("{sig}/N_spec_time vs MoSQITo"),
        );
    }
}

#[test]
fn zwtv_default_equals_golden_for_silent_tail_fixtures() {
    for sig in SILENT_TAIL {
        let x = read_bin(sig, "sig.bin");
        let r = loudness_zwtv(&x, 48000.0, FieldType::Free).unwrap();
        let c = mosqito_compatible(&x);
        assert_eq!(r.n, c.n, "{sig}: N must be bitwise identical");
        assert_eq!(
            r.n_specific, c.n_specific,
            "{sig}: N' must be bitwise identical"
        );
        assert_close(
            &r.n,
            &read_bin(sig, "N_time.bin"),
            0.0,
            COMPAT_TOL,
            &format!("{sig}/N_time default (compatibility)"),
        );
    }
}

#[test]
fn zwtv_default_converges_to_golden_once_the_tail_seed_has_decayed() {
    // On the 10 s Annex B fixtures the seeded slow capacitor has decayed below
    // the golden tolerance well before output frame 600 (measured first
    // sustained |dN| <= 1e-9: frame 482 for signal 3, 532 for signal 5, AVX2
    // default dispatch) and both paths are bitwise identical from frame 1002
    // (signal 3) / 980 (signal 5) onwards. The prefix is excluded here on
    // purpose: it is where the two initialisations differ by design, and
    // `tests/nl_zero_init.rs` is the gate for that region. (Measured on 0.3.1;
    // since 0.4.0 the comparison with the MoSQITo golden is a compatibility
    // check with COMPAT_TOL, and the bitwise default-vs-tail-seed check from
    // frame BITWISE on is the strict part of this test.)
    const SETTLED: usize = 600;
    const BITWISE: usize = 1100;
    for sig in ["annexb_sig3", "annexb_sig5"] {
        let x = read_bin(sig, "sig.bin");
        let want_n = read_bin(sig, "N_time.bin");
        let r = loudness_zwtv(&x, 48000.0, FieldType::Free).unwrap();
        assert!(r.n.len() > BITWISE + 1000, "{sig}: expected a 10 s fixture");
        assert_close(
            &r.n[SETTLED..],
            &want_n[SETTLED..],
            0.0,
            COMPAT_TOL,
            &format!("{sig}/N_time default from {SETTLED} (compatibility)"),
        );
        let c = mosqito_compatible(&x);
        for (i, (a, b)) in r.n.iter().zip(&c.n).enumerate().skip(BITWISE) {
            assert_eq!(a.to_bits(), b.to_bits(), "{sig}: frame {i}: {a} vs {b}");
        }
        assert_ne!(
            r.n[0].to_bits(),
            c.n[0].to_bits(),
            "{sig}: the two initialisations must still differ at the start"
        );
    }
}

/// Bitwise output snapshots on the AVX2 auto-dispatch path (fnv1a of n,
/// n_specific, time_axis). Rayon/Sequential are bitwise-equal (see determinism
/// tests), so these values do not depend on thread count.
///
/// `MOSQITO_TAIL` was recorded after R4 (commit e96dffa) when the tail seed was
/// the only batch behaviour; it is unchanged by F-02 and now pins
/// `NlInit::MosqitoTail`. `ZERO` was recorded on 2026-10-31 for the F-02
/// default. The two tables agree on the silent-tail fixtures, which is the
/// attribution for every changed value: only the seed differs.
///
/// 0.4.0 (2026-11-04) re-froze the `n` column of both tables after the slope
/// stage moved to Annex A (F-04/F-05); `n_specific` and `time_axis` hashes are
/// unchanged, which is the attribution: only the total loudness moved.
/// 0.4.0 Round 2 (F-07) re-froze only the `n_specific` column; `n` and
/// `time_axis` are unchanged, which is the attribution: only the specific
/// pattern moved.
/// Regenerate with
/// `cargo test --test golden_zwtv dump_zwtv_output_hashes -- --ignored --nocapture`.
const SNAPSHOT_AVX2_MOSQITO_TAIL: [(&str, u64, u64, u64); 4] = [
    (
        "sine_1k_60",
        0xf0b56048aedfa2bb,
        0x82acf1a81530f2c5,
        0xf076bcb342595537,
    ),
    (
        "pulse_1k_70",
        0xd22155cfcbf45989,
        0x3e6a9f727b2d1bc3,
        0xf076bcb342595537,
    ),
    (
        "step_60_80",
        0xfd9ae7beddca7080,
        0x83b401caf77e3832,
        0xf076bcb342595537,
    ),
    (
        "annexb_sig10",
        0x7a6a6f249051aec6,
        0x873ff274458f30fa,
        0xf076bcb342595537,
    ),
];

const SNAPSHOT_AVX2_ZERO: [(&str, u64, u64, u64); 4] = [
    (
        "sine_1k_60",
        0x27f8f4ebb33359e0,
        0x6754bac3c21024c8,
        0xf076bcb342595537,
    ),
    (
        "pulse_1k_70",
        0xd22155cfcbf45989,
        0x3e6a9f727b2d1bc3,
        0xf076bcb342595537,
    ),
    (
        "step_60_80",
        0x6a9a8c73bef27459,
        0x0ad9b8460aeda514,
        0xf076bcb342595537,
    ),
    (
        "annexb_sig10",
        0x7a6a6f249051aec6,
        0x873ff274458f30fa,
        0xf076bcb342595537,
    ),
];

fn assert_snapshot(
    table: &[(&str, u64, u64, u64); 4],
    run: impl Fn(&[f64]) -> iso532::LoudnessTimeVarying,
    label: &str,
) {
    for (sig, want_n, want_spec, want_time) in table {
        let x = read_bin(sig, "sig.bin");
        let r = run(&x);
        assert_eq!(fnv1a_f64(&r.n), *want_n, "{label} {sig}: N hash drifted");
        assert_eq!(
            fnv1a_f64(&r.n_specific),
            *want_spec,
            "{label} {sig}: N_specific hash drifted"
        );
        assert_eq!(
            fnv1a_f64(&r.time_axis),
            *want_time,
            "{label} {sig}: time hash drifted"
        );
    }
}

#[test]
fn zwtv_output_hashes_match_frozen_snapshots() {
    if !require_avx2_or_skip("zwtv_output_hashes_match_frozen_snapshots") {
        return;
    }
    assert_snapshot(
        &SNAPSHOT_AVX2_ZERO,
        |x| loudness_zwtv(x, 48000.0, FieldType::Free).unwrap(),
        "zero (default)",
    );
    assert_snapshot(
        &SNAPSHOT_AVX2_MOSQITO_TAIL,
        mosqito_compatible,
        "mosqito tail",
    );
    for (a, b) in SNAPSHOT_AVX2_ZERO.iter().zip(&SNAPSHOT_AVX2_MOSQITO_TAIL) {
        assert_eq!(a.0, b.0);
        let silent = SILENT_TAIL.contains(&a.0);
        assert_eq!(
            (a.1, a.2) == (b.1, b.2),
            silent,
            "{}: snapshots must agree exactly when (and only when) the tail is silent",
            a.0
        );
    }
}

#[test]
#[ignore = "manual helper: bitwise output snapshot for refactor verification"]
fn dump_zwtv_output_hashes() {
    for sig in ["sine_1k_60", "pulse_1k_70", "step_60_80", "annexb_sig10"] {
        let x = read_bin(sig, "sig.bin");
        for (label, r) in [
            ("zero", loudness_zwtv(&x, 48000.0, FieldType::Free).unwrap()),
            ("mosqito_tail", mosqito_compatible(&x)),
        ] {
            println!(
                "{sig} [{label}]: n={:016x} spec={:016x} time={:016x}",
                fnv1a_f64(&r.n),
                fnv1a_f64(&r.n_specific),
                fnv1a_f64(&r.time_axis),
            );
        }
    }
}
