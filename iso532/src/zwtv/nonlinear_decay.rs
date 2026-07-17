use super::ParMode;

const NL_ITER: usize = 24;
const SAMPLE_RATE: f64 = 2000.0;

/// Constants B[0..6] of the two-capacitor analog network.
pub fn nl_coeffs() -> [f64; 6] {
    let t_short: f64 = 0.005;
    let t_long: f64 = 0.015;
    let t_var: f64 = 0.075;
    let delta_t = 1.0 / (SAMPLE_RATE * NL_ITER as f64);
    let p = (t_var + t_long) / (t_var * t_short);
    let q = 1.0 / (t_short * t_var);
    let lambda_1 = -p / 2.0 + (p * p / 4.0 - q).sqrt();
    let lambda_2 = -p / 2.0 - (p * p / 4.0 - q).sqrt();
    let den = t_var * (lambda_1 - lambda_2);
    let e1 = (lambda_1 * delta_t).exp();
    let e2 = (lambda_2 * delta_t).exp();
    [
        (e1 - e2) / den,
        ((t_var * lambda_2 + 1.0) * e1 - (t_var * lambda_1 + 1.0) * e2) / den,
        ((t_var * lambda_1 + 1.0) * e1 - (t_var * lambda_2 + 1.0) * e2) / den,
        (t_var * lambda_1 + 1.0) * (t_var * lambda_2 + 1.0) * (e1 - e2) / den,
        (-delta_t / t_long).exp(),
        (-delta_t / t_var).exp(),
    ]
}

pub fn nl_loudness_scalar(core: &[f64], n_time: usize) -> Vec<f64> {
    nl_loudness_scalar_impl(core, n_time, ParMode::Sequential)
}

fn nl_loudness_scalar_impl(core: &[f64], n_time: usize, mode: ParMode) -> Vec<f64> {
    assert_eq!(
        core.len(),
        21 * n_time,
        "nl_loudness expects row-major (21, n_time) core loudness"
    );

    let b = nl_coeffs();
    let mut out = vec![0.0; core.len()];
    if n_time == 0 {
        return out;
    }

    super::chunks_dispatch(&mut out, n_time, mode, |band, out_row| {
        nl_loudness_band_scalar(&core[band * n_time..(band + 1) * n_time], out_row, &b);
    });

    out
}

#[derive(Clone, Copy, Debug, Default)]
pub(crate) struct NlBandState {
    prev_uo: f64,
    prev_u2: f64,
}

impl NlBandState {
    pub(crate) fn mosqito_seed(row_last: f64) -> Self {
        let delta = (0.0 - row_last) / NL_ITER as f64;
        Self {
            prev_uo: row_last + delta * (NL_ITER - 1) as f64,
            prev_u2: 0.0,
        }
    }

    #[inline]
    pub(crate) fn advance_frame(&mut self, row_t: f64, next: f64, b: &[f64; 6]) -> f64 {
        let delta = (next - row_t) / NL_ITER as f64;
        let mut out0 = 0.0;
        for k in 0..NL_ITER {
            let ui = row_t + delta * k as f64;
            let mut uo = ui;
            let uo2 = self.prev_uo * b[2] - self.prev_u2 * b[3];
            if self.prev_uo > self.prev_u2 && uo2 >= ui {
                uo = uo2;
            }
            let uo2 = self.prev_uo * b[4];
            if self.prev_uo <= self.prev_u2 && uo2 >= ui {
                uo = uo2;
            }
            let mut u2 = uo;
            let u22 = self.prev_uo * b[0] - self.prev_u2 * b[1];
            if ui < self.prev_uo && self.prev_uo > self.prev_u2 && u22 <= uo {
                u2 = u22;
            }
            let u2_2 = (self.prev_u2 - ui) * b[5] + ui;
            if ui >= self.prev_uo && !((ui - self.prev_uo).abs() < 1e-5 && uo <= self.prev_u2) {
                u2 = u2_2;
            }
            if k == 0 {
                out0 = uo;
            }
            self.prev_uo = uo;
            self.prev_u2 = u2;
        }
        out0
    }
}

fn nl_loudness_band_scalar(row: &[f64], out: &mut [f64], b: &[f64; 6]) {
    let n_time = row.len();
    assert_eq!(out.len(), n_time);
    if n_time == 0 {
        return;
    }
    let mut state = NlBandState::mosqito_seed(row[n_time - 1]);
    for t in 0..n_time {
        let next = if t + 1 < n_time { row[t + 1] } else { 0.0 };
        out[t] = state.advance_frame(row[t], next, b);
    }
}

/// AVX2+FMA nonlinear temporal decay kernel.
///
/// # Safety
/// Caller must ensure AVX2 and FMA are available before calling.
#[cfg(target_arch = "x86_64")]
pub unsafe fn nl_loudness_avx2(core: &[f64], n_time: usize, mode: ParMode) -> Vec<f64> {
    assert_eq!(
        core.len(),
        21 * n_time,
        "nl_loudness expects row-major (21, n_time) core loudness"
    );
    if n_time == 0 {
        return Vec::new();
    }

    let b = nl_coeffs();
    let mut out = vec![0.0; core.len()];

    super::chunks_dispatch(&mut out, 4 * n_time, mode, |g, group| {
        let n_bands = if 4 * g + 4 <= 21 { 4 } else { 21 - 4 * g };
        // SAFETY: dispatch has already verified AVX2+FMA availability.
        unsafe { nl_group_avx2(core, group, n_time, 4 * g, n_bands, b) };
    });

    out
}

/// Dispatch one output group: full 4-band groups use AVX2, the final single-band
/// tail uses scalar processing.
///
/// # Safety
/// Caller must ensure AVX2 and FMA are available before calling.
#[cfg(target_arch = "x86_64")]
unsafe fn nl_group_avx2(
    core: &[f64],
    group: &mut [f64],
    n_time: usize,
    band: usize,
    n_bands: usize,
    b: [f64; 6],
) {
    debug_assert_eq!(group.len(), n_bands * n_time);
    if n_bands == 4 {
        // SAFETY: caller has verified AVX2+FMA availability.
        unsafe { nl_loudness_process4(core, group, n_time, band, b) };
    } else {
        debug_assert_eq!(n_bands, 1);
        nl_loudness_band_scalar(&core[band * n_time..(band + 1) * n_time], group, &b);
    }
}

#[cfg(target_arch = "x86_64")]
#[inline]
#[target_feature(enable = "avx2,fma")]
unsafe fn nl_loudness_load4(
    core: &[f64],
    n_time: usize,
    band: usize,
    t: usize,
) -> std::arch::x86_64::__m256d {
    use std::arch::x86_64::*;

    _mm256_set_pd(
        core[(band + 3) * n_time + t],
        core[(band + 2) * n_time + t],
        core[(band + 1) * n_time + t],
        core[band * n_time + t],
    )
}

#[cfg(target_arch = "x86_64")]
pub(crate) struct NlConsts {
    b0: std::arch::x86_64::__m256d,
    b1: std::arch::x86_64::__m256d,
    b2: std::arch::x86_64::__m256d,
    b3: std::arch::x86_64::__m256d,
    b4: std::arch::x86_64::__m256d,
    b5: std::arch::x86_64::__m256d,
    inv_iter: std::arch::x86_64::__m256d,
    eps: std::arch::x86_64::__m256d,
}

#[cfg(target_arch = "x86_64")]
impl NlConsts {
    /// # Safety
    /// Caller must ensure AVX2 and FMA are available.
    #[target_feature(enable = "avx2,fma")]
    pub(crate) unsafe fn new(b: [f64; 6]) -> Self {
        use std::arch::x86_64::*;
        Self {
            b0: _mm256_set1_pd(b[0]),
            b1: _mm256_set1_pd(b[1]),
            b2: _mm256_set1_pd(b[2]),
            b3: _mm256_set1_pd(b[3]),
            b4: _mm256_set1_pd(b[4]),
            b5: _mm256_set1_pd(b[5]),
            inv_iter: _mm256_set1_pd(1.0 / NL_ITER as f64),
            eps: _mm256_set1_pd(1e-5),
        }
    }
}

#[cfg(target_arch = "x86_64")]
pub(crate) struct NlGroupState {
    prev_uo: std::arch::x86_64::__m256d,
    prev_u2: std::arch::x86_64::__m256d,
}

#[cfg(target_arch = "x86_64")]
impl NlGroupState {
    /// # Safety
    /// Caller must ensure AVX2 and FMA are available.
    #[target_feature(enable = "avx2,fma")]
    pub(crate) unsafe fn zero() -> Self {
        use std::arch::x86_64::*;
        Self {
            prev_uo: _mm256_setzero_pd(),
            prev_u2: _mm256_setzero_pd(),
        }
    }

    /// # Safety
    /// Caller must ensure AVX2 and FMA are available.
    #[target_feature(enable = "avx2,fma")]
    pub(crate) unsafe fn mosqito_seed(last_row: std::arch::x86_64::__m256d, c: &NlConsts) -> Self {
        use std::arch::x86_64::*;
        let last_delta = _mm256_mul_pd(_mm256_sub_pd(_mm256_setzero_pd(), last_row), c.inv_iter);
        Self {
            prev_uo: _mm256_fmadd_pd(last_delta, _mm256_set1_pd((NL_ITER - 1) as f64), last_row),
            prev_u2: _mm256_setzero_pd(),
        }
    }

    /// # Safety
    /// Caller must ensure AVX2 and FMA are available.
    #[inline]
    #[target_feature(enable = "avx2,fma")]
    pub(crate) unsafe fn advance_frame(
        &mut self,
        row: std::arch::x86_64::__m256d,
        next: std::arch::x86_64::__m256d,
        c: &NlConsts,
    ) -> std::arch::x86_64::__m256d {
        use std::arch::x86_64::*;
        let delta = _mm256_mul_pd(_mm256_sub_pd(next, row), c.inv_iter);
        let mut out0 = _mm256_setzero_pd();
        for k in 0..NL_ITER {
            let ui = _mm256_fmadd_pd(delta, _mm256_set1_pd(k as f64), row);
            let mut uo = ui;
            let uo2_fast = _mm256_fnmadd_pd(self.prev_u2, c.b3, _mm256_mul_pd(self.prev_uo, c.b2));
            let mask_fast = _mm256_and_pd(
                _mm256_cmp_pd(self.prev_uo, self.prev_u2, _CMP_GT_OQ),
                _mm256_cmp_pd(uo2_fast, ui, _CMP_GE_OQ),
            );
            uo = _mm256_blendv_pd(uo, uo2_fast, mask_fast);
            let uo2_slow = _mm256_mul_pd(self.prev_uo, c.b4);
            let mask_slow = _mm256_and_pd(
                _mm256_cmp_pd(self.prev_uo, self.prev_u2, _CMP_LE_OQ),
                _mm256_cmp_pd(uo2_slow, ui, _CMP_GE_OQ),
            );
            uo = _mm256_blendv_pd(uo, uo2_slow, mask_slow);
            let mut u2 = uo;
            let u22 = _mm256_fnmadd_pd(self.prev_u2, c.b1, _mm256_mul_pd(self.prev_uo, c.b0));
            let mask_u22 = _mm256_and_pd(
                _mm256_and_pd(
                    _mm256_cmp_pd(ui, self.prev_uo, _CMP_LT_OQ),
                    _mm256_cmp_pd(self.prev_uo, self.prev_u2, _CMP_GT_OQ),
                ),
                _mm256_cmp_pd(u22, uo, _CMP_LE_OQ),
            );
            u2 = _mm256_blendv_pd(u2, u22, mask_u22);
            let u2_2 = _mm256_fmadd_pd(_mm256_sub_pd(self.prev_u2, ui), c.b5, ui);
            let diff_abs = _mm256_andnot_pd(_mm256_set1_pd(-0.0), _mm256_sub_pd(ui, self.prev_uo));
            let near_and_not_higher = _mm256_and_pd(
                _mm256_cmp_pd(diff_abs, c.eps, _CMP_LT_OQ),
                _mm256_cmp_pd(uo, self.prev_u2, _CMP_LE_OQ),
            );
            let mask_u2_2 = _mm256_andnot_pd(
                near_and_not_higher,
                _mm256_cmp_pd(ui, self.prev_uo, _CMP_GE_OQ),
            );
            u2 = _mm256_blendv_pd(u2, u2_2, mask_u2_2);
            if k == 0 {
                out0 = uo;
            }
            self.prev_uo = uo;
            self.prev_u2 = u2;
        }
        out0
    }
}

#[cfg(target_arch = "x86_64")]
#[target_feature(enable = "avx2,fma")]
unsafe fn nl_loudness_process4(
    core: &[f64],
    out_group: &mut [f64],
    n_time: usize,
    band: usize,
    b: [f64; 6],
) {
    use std::arch::x86_64::*;

    debug_assert_eq!(out_group.len(), 4 * n_time);
    let c = unsafe { NlConsts::new(b) };
    let last = n_time - 1;
    let last_row = nl_loudness_load4(core, n_time, band, last);
    let mut state = unsafe { NlGroupState::mosqito_seed(last_row, &c) };

    for t in 0..n_time {
        let row = nl_loudness_load4(core, n_time, band, t);
        let next = if t + 1 < n_time {
            nl_loudness_load4(core, n_time, band, t + 1)
        } else {
            _mm256_setzero_pd()
        };
        let uo = unsafe { state.advance_frame(row, next, &c) };
        let mut lanes = [0.0; 4];
        _mm256_storeu_pd(lanes.as_mut_ptr(), uo);
        for lane in 0..4 {
            out_group[lane * n_time + t] = lanes[lane];
        }
    }
}

pub fn nl_loudness_with_mode(core: &[f64], n_time: usize, mode: ParMode) -> Vec<f64> {
    #[cfg(target_arch = "x86_64")]
    {
        if crate::simd::use_avx2() {
            return unsafe { nl_loudness_avx2(core, n_time, mode) };
        }
    }
    nl_loudness_scalar_impl(core, n_time, mode)
}

pub fn nl_loudness(core: &[f64], n_time: usize) -> Vec<f64> {
    nl_loudness_with_mode(core, n_time, ParMode::Rayon)
}
