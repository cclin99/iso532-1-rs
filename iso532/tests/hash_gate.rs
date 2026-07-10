#[allow(dead_code)]
mod common;

use iso532::{loudness_zwtv, simd, FieldType};

const FS: f64 = 48_000.0;

// Frozen bitwise snapshots of (fnv1a(n), fnv1a(n_specific), fnv1a(time_axis))
// for the synthetic signal below, one per backend and OS. Scalar and AVX2
// differ in ULP because FMA rounds once; Windows CRT and glibc libm
// (sin/powf/log10) differ in ULP as well. Each path must stay bitwise-stable
// against its own snapshot (refactor invariance, see risk report §8.4).
// Regenerate: set the pair to (0, 0, 0), run
// `cargo test --test hash_gate -- --nocapture`, copy the printed values.
#[cfg(target_os = "windows")]
const EXPECTED_SCALAR: (u64, u64, u64) =
    (0xf3215787aaa48fbe, 0xff98c57f3018ef94, 0xf076bcb342595537);
#[cfg(target_os = "windows")]
const EXPECTED_AVX2: (u64, u64, u64) = (0xf3215787aaa48fbe, 0x3f241da3fe334097, 0xf076bcb342595537);

#[cfg(target_os = "linux")]
const EXPECTED_SCALAR: (u64, u64, u64) =
    (0xf3215787aaa48fbe, 0x6e181dac593b5fef, 0xf076bcb342595537);
#[cfg(target_os = "linux")]
const EXPECTED_AVX2: (u64, u64, u64) = (0xf3215787aaa48fbe, 0x8213780cd5384fb0, 0xf076bcb342595537);

// unfrozen: regenerate per note above
#[cfg(not(any(target_os = "windows", target_os = "linux")))]
const EXPECTED_SCALAR: (u64, u64, u64) = (0, 0, 0);
#[cfg(not(any(target_os = "windows", target_os = "linux")))]
const EXPECTED_AVX2: (u64, u64, u64) = (0, 0, 0);

fn synth_signal() -> Vec<f64> {
    (0..48_000)
        .map(|i| {
            let t = i as f64 / FS;
            0.25 * (2.0 * std::f64::consts::PI * 440.0 * t).sin()
                + 0.10 * (2.0 * std::f64::consts::PI * 1_760.0 * t).sin()
                + 0.04 * (2.0 * std::f64::consts::PI * 6_400.0 * t).sin()
        })
        .collect()
}

fn run_hashes(signal: &[f64]) -> (u64, u64, u64) {
    let r = loudness_zwtv(signal, FS, FieldType::Free).unwrap();
    (
        common::fnv1a_f64(&r.n),
        common::fnv1a_f64(&r.n_specific),
        common::fnv1a_f64(&r.time_axis),
    )
}

// FORCE_SCALAR is process-global. Keep this integration test file to one
// #[test] so flag changes cannot race another test in this binary.
#[test]
fn zwtv_backend_hashes_match_frozen_snapshot() {
    let signal = synth_signal();

    // Compute and print both backends before asserting so a single failing
    // run (e.g. a new OS) still reveals every value needed to freeze.
    simd::set_force_scalar(true);
    let scalar = run_hashes(&signal);
    simd::set_force_scalar(false);
    eprintln!(
        "scalar: n={:#018x} spec={:#018x} time={:#018x}",
        scalar.0, scalar.1, scalar.2
    );

    let avx2 = if common::require_avx2_or_skip("zwtv_backend_hashes avx2") {
        let avx2 = run_hashes(&signal);
        eprintln!(
            "avx2:   n={:#018x} spec={:#018x} time={:#018x}",
            avx2.0, avx2.1, avx2.2
        );
        Some(avx2)
    } else {
        None
    };

    if EXPECTED_SCALAR == (0, 0, 0) {
        eprintln!("no frozen snapshot for this OS; dump-only run");
        return;
    }
    assert_eq!(scalar, EXPECTED_SCALAR, "scalar backend hash drifted");
    if let Some(avx2) = avx2 {
        assert_eq!(avx2, EXPECTED_AVX2, "avx2 backend hash drifted");
    }
}
