#[allow(dead_code)]
mod common;

use common::assert_close;
use iso532::zwtv::nonlinear_decay::{nl_loudness_avx2, nl_loudness_scalar};
use iso532::zwtv::third_octave_levels::{third_octave_levels_avx2, third_octave_levels_scalar};
use iso532::zwtv::ParMode;

#[test]
fn filter_bank_avx2_matches_scalar() {
    if !iso532::simd::avx2_available() {
        eprintln!("AVX2 not available; skipping");
        return;
    }

    let mut state = 0x12345678u64;
    let sig: Vec<f64> = (0..48_000)
        .map(|_| {
            state = state
                .wrapping_mul(6364136223846793005)
                .wrapping_add(1442695040888963407);
            ((state >> 11) as f64 / (1u64 << 53) as f64 - 0.5) * 0.02
        })
        .collect();

    let (scalar, scalar_n_time) = third_octave_levels_scalar(&sig);
    let (avx2, avx2_n_time) = unsafe { third_octave_levels_avx2(&sig, ParMode::Sequential) };

    assert_eq!(avx2_n_time, scalar_n_time);
    assert_close(&avx2, &scalar, 1e-10, 1e-12, "avx2 vs scalar");
}

#[test]
fn nl_loudness_avx2_matches_scalar() {
    if !iso532::simd::avx2_available() {
        eprintln!("AVX2 not available; skipping");
        return;
    }

    let n_time = 500usize;
    let mut core = vec![0.0; 21 * n_time];
    for band in 0..21 {
        for t in 0..n_time {
            let phase = (t as f64 / 40.0 + band as f64).sin();
            core[band * n_time + t] = (phase * 0.6 + 0.5).max(0.0);
        }
    }

    let scalar = nl_loudness_scalar(&core, n_time);
    let avx2 = unsafe { nl_loudness_avx2(&core, n_time, ParMode::Sequential) };
    assert_close(&avx2, &scalar, 1e-12, 1e-14, "nl avx2 vs scalar");
}
