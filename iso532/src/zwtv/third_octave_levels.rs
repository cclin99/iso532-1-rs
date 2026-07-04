use crate::dsp::sos::{onepole, sosfilt, Sos};
use crate::tables::{N_TOB_BANDS, TOB_DELTA, TOB_GAIN};

pub const DEC_FACTOR: usize = 24;
const FS: f64 = 48_000.0;
const TINY: f64 = 1e-12;
const I_REF: f64 = 4e-10;

/// Reference-filter b coefficients per section (ISO 532-1 Table A.1).
pub const TOB_B: [[f64; 3]; 3] = [[1.0, 2.0, 1.0], [1.0, 0.0, -1.0], [1.0, -2.0, 1.0]];

fn band_sos(band: usize) -> [Sos; 3] {
    std::array::from_fn(|section| Sos {
        b: TOB_B[section],
        a: [
            -2.0 - TOB_DELTA[band][section][0],
            1.0 - TOB_DELTA[band][section][1],
        ],
    })
}

pub fn center_frequency(band: usize) -> f64 {
    10.0_f64.powf((band as f64 - 16.0) / 10.0) * 1000.0
}

pub fn smoothing_coeff(band: usize) -> (f64, f64) {
    let fc = center_frequency(band);
    let tau = 2.0 / (3.0 * fc.min(1000.0));
    let a1 = (-1.0 / (FS * tau)).exp();
    (1.0 - a1, a1)
}

pub fn third_octave_levels_scalar(sig: &[f64]) -> (Vec<f64>, usize) {
    let n_time = sig.len().div_ceil(DEC_FACTOR);
    let mut out = vec![0.0; N_TOB_BANDS * n_time];

    for band in 0..N_TOB_BANDS {
        let mut x: Vec<f64> = sig.iter().map(|v| v * TOB_GAIN[band]).collect();
        sosfilt(&band_sos(band), &mut x);

        for v in &mut x {
            *v *= *v;
        }

        let (b0, a1) = smoothing_coeff(band);
        for _ in 0..3 {
            onepole(b0, a1, &mut x);
        }

        for (t, v) in x.iter().step_by(DEC_FACTOR).enumerate() {
            out[band * n_time + t] = 10.0 * ((*v + TINY) / I_REF).log10();
        }
    }

    (out, n_time)
}

/// AVX2+FMA filter bank kernel processing 28 bands as 7 vectors of f64x4.
///
/// # Safety
/// Caller must ensure AVX2 and FMA are available before calling.
#[cfg(target_arch = "x86_64")]
#[target_feature(enable = "avx2,fma")]
pub unsafe fn third_octave_levels_avx2(sig: &[f64]) -> (Vec<f64>, usize) {
    use std::arch::x86_64::*;

    const NV: usize = 7;
    let n_time = sig.len().div_ceil(DEC_FACTOR);
    let mut out = vec![0.0; N_TOB_BANDS * n_time];

    let mut gain = [_mm256_setzero_pd(); NV];
    let mut a1 = [[_mm256_setzero_pd(); NV]; 3];
    let mut a2 = [[_mm256_setzero_pd(); NV]; 3];
    let mut sb0 = [_mm256_setzero_pd(); NV];
    let mut sa1 = [_mm256_setzero_pd(); NV];

    for v in 0..NV {
        let mut g = [0.0; 4];
        let mut b0s = [0.0; 4];
        let mut a1s = [0.0; 4];
        let mut a1c = [[0.0; 4]; 3];
        let mut a2c = [[0.0; 4]; 3];
        for lane in 0..4 {
            let band = 4 * v + lane;
            g[lane] = TOB_GAIN[band];
            let (b0, smooth_a1) = smoothing_coeff(band);
            b0s[lane] = b0;
            a1s[lane] = smooth_a1;
            for section in 0..3 {
                a1c[section][lane] = -2.0 - TOB_DELTA[band][section][0];
                a2c[section][lane] = 1.0 - TOB_DELTA[band][section][1];
            }
        }
        gain[v] = _mm256_loadu_pd(g.as_ptr());
        sb0[v] = _mm256_loadu_pd(b0s.as_ptr());
        sa1[v] = _mm256_loadu_pd(a1s.as_ptr());
        for section in 0..3 {
            a1[section][v] = _mm256_loadu_pd(a1c[section].as_ptr());
            a2[section][v] = _mm256_loadu_pd(a2c[section].as_ptr());
        }
    }

    let b1s = [2.0, 0.0, -2.0];
    let b2s = [1.0, -1.0, 1.0];
    let mut z0 = [[_mm256_setzero_pd(); NV]; 3];
    let mut z1 = [[_mm256_setzero_pd(); NV]; 3];
    let mut sm = [[_mm256_setzero_pd(); NV]; 3];

    let mut frame = 0usize;
    for (i, &sample) in sig.iter().enumerate() {
        let xs = _mm256_set1_pd(sample);
        let store = i % DEC_FACTOR == 0;
        for v in 0..NV {
            let mut y = _mm256_mul_pd(xs, gain[v]);
            for section in 0..3 {
                let xin = y;
                y = _mm256_add_pd(xin, z0[section][v]);
                let b1v = _mm256_set1_pd(b1s[section]);
                let t = _mm256_fmadd_pd(b1v, xin, z1[section][v]);
                z0[section][v] = _mm256_fnmadd_pd(a1[section][v], y, t);
                let b2v = _mm256_set1_pd(b2s[section]);
                z1[section][v] = _mm256_fnmadd_pd(a2[section][v], y, _mm256_mul_pd(b2v, xin));
            }

            y = _mm256_mul_pd(y, y);
            for stage_state in &mut sm {
                stage_state[v] = _mm256_fmadd_pd(sb0[v], y, _mm256_mul_pd(sa1[v], stage_state[v]));
                y = stage_state[v];
            }

            if store {
                let mut lanes = [0.0; 4];
                _mm256_storeu_pd(lanes.as_mut_ptr(), y);
                for lane in 0..4 {
                    out[(4 * v + lane) * n_time + frame] =
                        10.0 * ((lanes[lane] + TINY) / I_REF).log10();
                }
            }
        }
        if store {
            frame += 1;
        }
    }

    (out, n_time)
}

pub fn third_octave_levels(sig: &[f64]) -> (Vec<f64>, usize) {
    #[cfg(target_arch = "x86_64")]
    if crate::simd::use_avx2() {
        return unsafe { third_octave_levels_avx2(sig) };
    }
    third_octave_levels_scalar(sig)
}

pub fn time_axis(_sig_len: usize, n_time: usize) -> Vec<f64> {
    (0..n_time).map(|i| (i * DEC_FACTOR) as f64 / FS).collect()
}
