use super::ParMode;
use crate::dsp::sos::Sos;
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

pub(crate) struct TolBandState {
    sos: [Sos; 3],
    z: [[f64; 2]; 3],
    gain: f64,
    sb0: f64,
    sa1: f64,
    sm: [f64; 3],
}

impl TolBandState {
    pub(crate) fn new(band: usize) -> Self {
        let (sb0, sa1) = smoothing_coeff(band);
        Self {
            sos: band_sos(band),
            z: [[0.0; 2]; 3],
            gain: TOB_GAIN[band],
            sb0,
            sa1,
            sm: [0.0; 3],
        }
    }

    #[inline]
    pub(crate) fn advance(&mut self, sample: f64) -> f64 {
        let mut v = sample * self.gain;
        for (s, z) in self.sos.iter().zip(self.z.iter_mut()) {
            let xin = v;
            let y = s.b[0] * xin + z[0];
            z[0] = s.b[1] * xin - s.a[0] * y + z[1];
            z[1] = s.b[2] * xin - s.a[1] * y;
            v = y;
        }
        v *= v;
        for stage in &mut self.sm {
            *stage = self.sb0 * v + self.sa1 * *stage;
            v = *stage;
        }
        v
    }
}

#[inline]
pub(crate) fn intensity_to_db(v: f64) -> f64 {
    10.0 * ((v + TINY) / I_REF).log10()
}

fn tol_band_scalar(sig: &[f64], band: usize, out_row: &mut [f64]) {
    let mut state = TolBandState::new(band);
    let mut frame = 0;
    for (i, &sample) in sig.iter().enumerate() {
        let v = state.advance(sample);
        if i % DEC_FACTOR == 0 {
            out_row[frame] = intensity_to_db(v);
            frame += 1;
        }
    }
}

pub fn third_octave_levels_scalar(sig: &[f64]) -> (Vec<f64>, usize) {
    third_octave_levels_scalar_impl(sig, ParMode::Sequential)
}

fn third_octave_levels_scalar_impl(sig: &[f64], mode: ParMode) -> (Vec<f64>, usize) {
    let n_time = sig.len().div_ceil(DEC_FACTOR);
    let mut out = vec![0.0; N_TOB_BANDS * n_time];
    if n_time == 0 {
        return (out, 0);
    }

    super::chunks_dispatch(&mut out, n_time, mode, |band, out_row| {
        tol_band_scalar(sig, band, out_row)
    });

    (out, n_time)
}

/// Single f64x4 group (bands 4v..4v+4) AVX2+FMA filter bank kernel.
///
/// # Safety
/// Caller must ensure AVX2 and FMA are available before calling.
#[cfg(target_arch = "x86_64")]
pub(crate) struct TolGroupState {
    gain: std::arch::x86_64::__m256d,
    sb0: std::arch::x86_64::__m256d,
    sa1: std::arch::x86_64::__m256d,
    a1: [std::arch::x86_64::__m256d; 3],
    a2: [std::arch::x86_64::__m256d; 3],
    z0: [std::arch::x86_64::__m256d; 3],
    z1: [std::arch::x86_64::__m256d; 3],
    sm: [std::arch::x86_64::__m256d; 3],
}

#[cfg(target_arch = "x86_64")]
impl TolGroupState {
    /// # Safety
    /// Caller must ensure AVX2 and FMA are available.
    #[target_feature(enable = "avx2,fma")]
    pub(crate) unsafe fn new(v: usize) -> Self {
        use std::arch::x86_64::*;

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
        let mut a1 = [_mm256_setzero_pd(); 3];
        let mut a2 = [_mm256_setzero_pd(); 3];
        for section in 0..3 {
            a1[section] = _mm256_loadu_pd(a1c[section].as_ptr());
            a2[section] = _mm256_loadu_pd(a2c[section].as_ptr());
        }
        Self {
            gain: _mm256_loadu_pd(g.as_ptr()),
            sb0: _mm256_loadu_pd(b0s.as_ptr()),
            sa1: _mm256_loadu_pd(a1s.as_ptr()),
            a1,
            a2,
            z0: [_mm256_setzero_pd(); 3],
            z1: [_mm256_setzero_pd(); 3],
            sm: [_mm256_setzero_pd(); 3],
        }
    }

    /// # Safety
    /// Caller must ensure AVX2 and FMA are available.
    #[inline]
    #[target_feature(enable = "avx2,fma")]
    pub(crate) unsafe fn advance(&mut self, sample: f64) -> std::arch::x86_64::__m256d {
        use std::arch::x86_64::*;

        let xs = _mm256_set1_pd(sample);
        let mut y = _mm256_mul_pd(xs, self.gain);
        let b1s = [2.0, 0.0, -2.0];
        let b2s = [1.0, -1.0, 1.0];
        for section in 0..3 {
            let xin = y;
            y = _mm256_add_pd(xin, self.z0[section]);
            let b1v = _mm256_set1_pd(b1s[section]);
            let t = _mm256_fmadd_pd(b1v, xin, self.z1[section]);
            self.z0[section] = _mm256_fnmadd_pd(self.a1[section], y, t);
            let b2v = _mm256_set1_pd(b2s[section]);
            self.z1[section] = _mm256_fnmadd_pd(self.a2[section], y, _mm256_mul_pd(b2v, xin));
        }
        y = _mm256_mul_pd(y, y);
        for stage_state in &mut self.sm {
            *stage_state = _mm256_fmadd_pd(self.sb0, y, _mm256_mul_pd(self.sa1, *stage_state));
            y = *stage_state;
        }
        y
    }
}

#[cfg(target_arch = "x86_64")]
#[target_feature(enable = "avx2,fma")]
unsafe fn tol_group_avx2(sig: &[f64], v: usize, out_group: &mut [f64], n_time: usize) {
    use std::arch::x86_64::*;

    debug_assert_eq!(out_group.len(), 4 * n_time);
    let mut state = unsafe { TolGroupState::new(v) };

    let mut frame = 0usize;
    for (i, &sample) in sig.iter().enumerate() {
        let y = unsafe { state.advance(sample) };
        if i % DEC_FACTOR == 0 {
            let mut lanes = [0.0; 4];
            _mm256_storeu_pd(lanes.as_mut_ptr(), y);
            for lane in 0..4 {
                out_group[lane * n_time + frame] = intensity_to_db(lanes[lane]);
            }
            frame += 1;
        }
    }
}

/// AVX2+FMA filter bank: 28 bands as 7 independent f64x4 groups.
///
/// # Safety
/// Caller must ensure AVX2 and FMA are available before calling.
#[cfg(target_arch = "x86_64")]
pub unsafe fn third_octave_levels_avx2(sig: &[f64], mode: ParMode) -> (Vec<f64>, usize) {
    let n_time = sig.len().div_ceil(DEC_FACTOR);
    let mut out = vec![0.0; N_TOB_BANDS * n_time];
    if n_time == 0 {
        return (out, 0);
    }

    super::chunks_dispatch(&mut out, 4 * n_time, mode, |v, group| {
        // SAFETY: dispatch has already verified AVX2+FMA availability.
        unsafe { tol_group_avx2(sig, v, group, n_time) };
    });

    (out, n_time)
}

pub fn third_octave_levels_with_mode(sig: &[f64], mode: ParMode) -> (Vec<f64>, usize) {
    #[cfg(target_arch = "x86_64")]
    if crate::simd::use_avx2() {
        return unsafe { third_octave_levels_avx2(sig, mode) };
    }
    third_octave_levels_scalar_impl(sig, mode)
}

pub fn third_octave_levels(sig: &[f64]) -> (Vec<f64>, usize) {
    third_octave_levels_with_mode(sig, ParMode::Rayon)
}

pub fn time_axis(_sig_len: usize, n_time: usize) -> Vec<f64> {
    (0..n_time).map(|i| (i * DEC_FACTOR) as f64 / FS).collect()
}
