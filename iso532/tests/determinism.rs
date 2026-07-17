#[allow(dead_code)]
mod common;

use iso532::zwtv::nonlinear_decay::nl_loudness_with_mode;
use iso532::zwtv::third_octave_levels::third_octave_levels_with_mode;
use iso532::zwtv::ParMode;
use iso532::{loudness_zwtv, simd, FieldType};

const FS: f64 = 48_000.0;

fn assert_tol_modes_bitwise_equal(signal: &[f64]) {
    let (r, n_r) = third_octave_levels_with_mode(signal, ParMode::Rayon);
    let (s, n_s) = third_octave_levels_with_mode(signal, ParMode::Sequential);
    assert_eq!(n_r, n_s, "tol n_time");
    assert_eq!(r.len(), s.len(), "tol len");
    for (i, (a, b)) in r.iter().zip(&s).enumerate() {
        assert_eq!(
            a.to_bits(),
            b.to_bits(),
            "tol[{i}]: Rayon={a:e} Sequential={b:e}"
        );
    }
}

fn assert_nl_modes_bitwise_equal() {
    let n_time = 500;
    let core = common::synth_core(n_time);
    let r = nl_loudness_with_mode(&core, n_time, ParMode::Rayon);
    let s = nl_loudness_with_mode(&core, n_time, ParMode::Sequential);
    for (i, (a, b)) in r.iter().zip(&s).enumerate() {
        assert_eq!(
            a.to_bits(),
            b.to_bits(),
            "nl[{i}]: Rayon={a:e} Sequential={b:e}"
        );
    }
}

fn run_hashes(signal: &[f64]) -> (u64, u64, u64) {
    let r = loudness_zwtv(signal, FS, FieldType::Free).unwrap();
    (
        common::fnv1a_f64(&r.n),
        common::fnv1a_f64(&r.n_specific),
        common::fnv1a_f64(&r.time_axis),
    )
}

fn assert_20_runs_identical(signal: &[f64], ctx: &str) {
    let first = run_hashes(signal);
    for run in 1..20 {
        assert_eq!(run_hashes(signal), first, "{ctx}: run {run} diverged");
    }
}

// FORCE_SCALAR is process-global. Keep this integration test file to one
// #[test] so flag changes cannot race another test in this binary.
#[test]
fn zwtv_output_is_bitwise_deterministic_over_20_runs() {
    let signal = common::synth_signal();

    assert_tol_modes_bitwise_equal(&signal);
    assert_nl_modes_bitwise_equal();
    assert_20_runs_identical(&signal, "auto dispatch");

    simd::set_force_scalar(true);
    assert_tol_modes_bitwise_equal(&signal);
    assert_nl_modes_bitwise_equal();
    assert_20_runs_identical(&signal, "forced scalar");
    simd::set_force_scalar(false);
}
