#[allow(dead_code)]
mod common;

use iso532::zwtv::NlInit;
use iso532::{simd, FieldType, ZwtvProcessor};

const FS: f64 = 48_000.0;

// Frozen bitwise snapshots of (fnv1a(n), fnv1a(n_specific), fnv1a(time_axis))
// for the synthetic signal below, one per backend, OS and nonlinear-decay
// initialisation. Scalar and AVX2 differ in ULP because FMA rounds once; libm
// (sin/powf/log10) differs in ULP across platforms as well. Each path must
// stay bitwise-stable against its own snapshot (refactor invariance, see risk
// report §8.4).
//
// Scope of the contract: time_axis is bitwise-identical across every
// environment tested. n_specific carries libm ULP noise, and since 0.4.0 so
// does n: until 0.3.1 the per-frame rounding of the total to 0.001 sone (F-04)
// hid that noise, so n used to agree across backends and OSes. glibc
// values are stable across machines (frozen from ubuntu:24.04, matches GitHub
// runners). Windows UCRT dispatches libm by CPU and varies by OS build, so
// the windows constants only hold on the machine that froze them — windows CI
// therefore runs dump-only via HASH_GATE_DUMP_ONLY=1 (see .github/workflows/
// ci.yml); a different dev machine should re-freeze locally.
//
// `*_MOSQITO_TAIL` are the values frozen in July 2026 when the MoSQITo tail
// seed was the only batch behaviour; F-02 (2026-10-31) left them untouched and
// they now pin `NlInit::MosqitoTail`. The default (`NlInit::Zero`) constants
// were frozen on 2026-10-31 (windows: this machine; linux: ubuntu:24.04
// container, glibc 2.39). Only `n` and `n_specific` moved; `time_axis` is
// unchanged. 0.4.0 (2026-11-04) re-froze only `n` of all eight constants after
// the slope stage moved to Annex A (F-04/F-05); `n_specific` and `time_axis`
// are unchanged (windows: this machine; linux: ubuntu:24.04 container, glibc
// 2.39, rustc 1.99.1). Regenerate: set a pair to (0, 0, 0), run
// `cargo test --test hash_gate -- --nocapture`, copy the printed values.
#[cfg(target_os = "windows")]
const EXPECTED_SCALAR: (u64, u64, u64) =
    (0xde3ccbba47ec9dd5, 0x16937b45e6e4155d, 0xf076bcb342595537);
#[cfg(target_os = "windows")]
const EXPECTED_AVX2: (u64, u64, u64) = (0x917cc80e33295cc3, 0x3d4b4b2df9073e48, 0xf076bcb342595537);
#[cfg(target_os = "windows")]
const EXPECTED_SCALAR_MOSQITO_TAIL: (u64, u64, u64) =
    (0xb62e33532ef3019a, 0xff98c57f3018ef94, 0xf076bcb342595537);
#[cfg(target_os = "windows")]
const EXPECTED_AVX2_MOSQITO_TAIL: (u64, u64, u64) =
    (0x441d7721a9a22ffc, 0x3f241da3fe334097, 0xf076bcb342595537);

#[cfg(target_os = "linux")]
const EXPECTED_SCALAR: (u64, u64, u64) =
    (0x6b40a36a3d846e23, 0x05dc55b516e20132, 0xf076bcb342595537);
#[cfg(target_os = "linux")]
const EXPECTED_AVX2: (u64, u64, u64) = (0x284854f5f5758f91, 0x197c1084aab28c59, 0xf076bcb342595537);
#[cfg(target_os = "linux")]
const EXPECTED_SCALAR_MOSQITO_TAIL: (u64, u64, u64) =
    (0x00af090992c2d076, 0x6e181dac593b5fef, 0xf076bcb342595537);
#[cfg(target_os = "linux")]
const EXPECTED_AVX2_MOSQITO_TAIL: (u64, u64, u64) =
    (0xa59f12960442c5cc, 0x8213780cd5384fb0, 0xf076bcb342595537);

// unfrozen: regenerate per note above
#[cfg(not(any(target_os = "windows", target_os = "linux")))]
const EXPECTED_SCALAR: (u64, u64, u64) = (0, 0, 0);
#[cfg(not(any(target_os = "windows", target_os = "linux")))]
const EXPECTED_AVX2: (u64, u64, u64) = (0, 0, 0);
#[cfg(not(any(target_os = "windows", target_os = "linux")))]
const EXPECTED_SCALAR_MOSQITO_TAIL: (u64, u64, u64) = (0, 0, 0);
#[cfg(not(any(target_os = "windows", target_os = "linux")))]
const EXPECTED_AVX2_MOSQITO_TAIL: (u64, u64, u64) = (0, 0, 0);

fn run_hashes(signal: &[f64], init: NlInit) -> (u64, u64, u64) {
    let r = ZwtvProcessor::new()
        .process_with(signal, FS, FieldType::Free, init)
        .unwrap();
    (
        common::fnv1a_f64(&r.n),
        common::fnv1a_f64(&r.n_specific),
        common::fnv1a_f64(&r.time_axis),
    )
}

fn print(label: &str, h: (u64, u64, u64)) {
    eprintln!(
        "{label}: n={:#018x} spec={:#018x} time={:#018x}",
        h.0, h.1, h.2
    );
}

// FORCE_SCALAR is process-global. Keep this integration test file to one
// #[test] so flag changes cannot race another test in this binary.
#[test]
fn zwtv_backend_hashes_match_frozen_snapshot() {
    let signal = common::synth_signal();

    // Compute and print every value before asserting so a single failing
    // run (e.g. a new OS) still reveals every value needed to freeze.
    simd::set_force_scalar(true);
    let scalar = run_hashes(&signal, NlInit::Zero);
    let scalar_tail = run_hashes(&signal, NlInit::MosqitoTail);
    simd::set_force_scalar(false);
    print("scalar", scalar);
    print("scalar mosqito_tail", scalar_tail);

    let avx2 = if common::require_avx2_or_skip("zwtv_backend_hashes avx2") {
        let avx2 = run_hashes(&signal, NlInit::Zero);
        let avx2_tail = run_hashes(&signal, NlInit::MosqitoTail);
        print("avx2", avx2);
        print("avx2 mosqito_tail", avx2_tail);
        Some((avx2, avx2_tail))
    } else {
        None
    };

    let dump_only = EXPECTED_SCALAR == (0, 0, 0)
        || std::env::var("HASH_GATE_DUMP_ONLY").is_ok_and(|v| v == "1");
    if dump_only {
        eprintln!("hash gate: dump-only run (no frozen snapshot for this environment)");
        return;
    }
    assert_eq!(scalar, EXPECTED_SCALAR, "scalar backend hash drifted");
    assert_eq!(
        scalar_tail, EXPECTED_SCALAR_MOSQITO_TAIL,
        "scalar backend (mosqito tail) hash drifted"
    );
    if let Some((avx2, avx2_tail)) = avx2 {
        assert_eq!(avx2, EXPECTED_AVX2, "avx2 backend hash drifted");
        assert_eq!(
            avx2_tail, EXPECTED_AVX2_MOSQITO_TAIL,
            "avx2 backend (mosqito tail) hash drifted"
        );
    }
}
