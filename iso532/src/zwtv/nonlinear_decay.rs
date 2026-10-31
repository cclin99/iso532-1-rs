use super::ParMode;

/// Initial state of the nonlinear temporal decay (ISO 532-1 Annex A, the two
/// capacitor voltages `UoLast` / `U2Last` of each critical band) before the
/// first frame of a batch run.
///
/// The stream path always starts from zero state; this choice only affects
/// `loudness_zwtv` / `ZwtvProcessor`.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum NlInit {
    /// Zero state, as in the Annex A C program. Default. The output for a
    /// signal prefix does not depend on the samples that follow it, and the
    /// batch result equals the causal stream from the first frame.
    #[default]
    Zero,
    /// Seed every band with `core[n_time - 1] / 24`, which is what MoSQITo
    /// 1.2.1 computes because its vectorised first column reads column `-1`.
    /// Finding F-02 (2026-10-31); kept so that the MoSQITo golden fixtures and
    /// the direct MoSQITo parity suite stay bitwise comparable. Not intended
    /// for measurement use: the first ~0.1-0.5 s of the result depend on the
    /// end of the signal.
    MosqitoTail,
}

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
    nl_loudness_scalar_with(core, n_time, NlInit::Zero)
}

pub fn nl_loudness_scalar_with(core: &[f64], n_time: usize, init: NlInit) -> Vec<f64> {
    nl_loudness_scalar_impl(core, n_time, ParMode::Sequential, init)
}

fn nl_loudness_scalar_impl(core: &[f64], n_time: usize, mode: ParMode, init: NlInit) -> Vec<f64> {
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
        nl_loudness_band_scalar(&core[band * n_time..(band + 1) * n_time], out_row, &b, init);
    });

    out
}

#[derive(Clone, Copy, Debug, Default)]
pub(crate) struct NlBandState {
    prev_uo: f64,
    prev_u2: f64,
}

impl NlBandState {
    pub(crate) fn seed(init: NlInit, row_last: f64) -> Self {
        match init {
            NlInit::Zero => Self::default(),
            NlInit::MosqitoTail => Self::mosqito_seed(row_last),
        }
    }

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

fn nl_loudness_band_scalar(row: &[f64], out: &mut [f64], b: &[f64; 6], init: NlInit) {
    let n_time = row.len();
    assert_eq!(out.len(), n_time);
    if n_time == 0 {
        return;
    }
    let mut state = NlBandState::seed(init, row[n_time - 1]);
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
pub unsafe fn nl_loudness_avx2(
    core: &[f64],
    n_time: usize,
    mode: ParMode,
    init: NlInit,
) -> Vec<f64> {
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
        unsafe { nl_group_avx2(core, group, n_time, 4 * g, n_bands, b, init) };
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
    init: NlInit,
) {
    debug_assert_eq!(group.len(), n_bands * n_time);
    if n_bands == 4 {
        // SAFETY: caller has verified AVX2+FMA availability.
        unsafe { nl_loudness_process4(core, group, n_time, band, b, init) };
    } else {
        debug_assert_eq!(n_bands, 1);
        nl_loudness_band_scalar(&core[band * n_time..(band + 1) * n_time], group, &b, init);
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
    pub(crate) unsafe fn seed(
        init: NlInit,
        last_row: std::arch::x86_64::__m256d,
        c: &NlConsts,
    ) -> Self {
        match init {
            NlInit::Zero => unsafe { Self::zero() },
            NlInit::MosqitoTail => unsafe { Self::mosqito_seed(last_row, c) },
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
    init: NlInit,
) {
    use std::arch::x86_64::*;

    debug_assert_eq!(out_group.len(), 4 * n_time);
    let c = unsafe { NlConsts::new(b) };
    let last = n_time - 1;
    let last_row = nl_loudness_load4(core, n_time, band, last);
    let mut state = unsafe { NlGroupState::seed(init, last_row, &c) };

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

pub fn nl_loudness_with(core: &[f64], n_time: usize, mode: ParMode, init: NlInit) -> Vec<f64> {
    #[cfg(target_arch = "x86_64")]
    {
        if crate::simd::use_avx2() {
            return unsafe { nl_loudness_avx2(core, n_time, mode, init) };
        }
    }
    nl_loudness_scalar_impl(core, n_time, mode, init)
}

pub fn nl_loudness_with_mode(core: &[f64], n_time: usize, mode: ParMode) -> Vec<f64> {
    nl_loudness_with(core, n_time, mode, NlInit::Zero)
}

pub fn nl_loudness(core: &[f64], n_time: usize) -> Vec<f64> {
    nl_loudness_with_mode(core, n_time, ParMode::Rayon)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn core_from_rows(rows: &[Vec<f64>]) -> (Vec<f64>, usize) {
        let n_time = rows[0].len();
        let mut core = Vec::with_capacity(21 * n_time);
        for band in 0..21 {
            let row = &rows[band % rows.len()];
            assert_eq!(row.len(), n_time);
            core.extend_from_slice(row);
        }
        (core, n_time)
    }

    #[test]
    fn zero_init_default_and_mosqito_seed_formula() {
        assert_eq!(NlInit::default(), NlInit::Zero);
        let s = NlBandState::seed(NlInit::Zero, 2.4);
        assert_eq!((s.prev_uo, s.prev_u2), (0.0, 0.0));
        let s = NlBandState::seed(NlInit::MosqitoTail, 2.4);
        // core[-1] + (0 - core[-1]) / 24 * 23 == core[-1] / 24 up to rounding
        assert!((s.prev_uo - 0.1).abs() < 1e-15, "{}", s.prev_uo);
        assert_eq!(s.prev_u2, 0.0);
    }

    #[test]
    fn single_and_two_frame_inputs_do_not_panic_and_start_from_zero() {
        for rows in [vec![vec![0.7]], vec![vec![0.7, 0.0]], vec![vec![0.0, 0.7]]] {
            let (core, n_time) = core_from_rows(&rows);
            let out = nl_loudness_scalar(&core, n_time);
            assert_eq!(out.len(), core.len());
            // first output equals the first input (zero state never exceeds it)
            assert_eq!(out[0], core[0]);
            assert!(out.iter().all(|v| v.is_finite()));
        }
        assert!(nl_loudness_scalar(&[], 0).is_empty());
    }

    #[test]
    fn silent_tail_makes_both_initialisations_identical() {
        let mut row = vec![1.5; 200];
        row[100..].fill(0.0);
        let (core, n_time) = core_from_rows(&[row]);
        let zero = nl_loudness_scalar(&core, n_time);
        let tail = nl_loudness_scalar_with(&core, n_time, NlInit::MosqitoTail);
        assert_eq!(zero, tail);
    }

    #[test]
    fn tail_seed_only_changes_the_start_of_the_output() {
        // constant input: zero state outputs the input from frame 0; the tail
        // seed (1.5 / 24) is below the input and is overridden immediately on
        // the output but lives on in the slow capacitor.
        let (core, n_time) = core_from_rows(&[vec![1.5; 400]]);
        let zero = nl_loudness_scalar(&core, n_time);
        let tail = nl_loudness_scalar_with(&core, n_time, NlInit::MosqitoTail);
        assert!(zero.iter().all(|&v| v == 1.5));
        assert_eq!(zero[0], 1.5);
        assert_ne!(
            zero.iter().zip(&tail).filter(|(a, b)| a != b).count(),
            zero.len(),
            "difference must not be everywhere"
        );
        // A loud first frame overwrites the seeded fast capacitor at once; only
        // a quiet start exposes it (the batch filter start-up frames are quiet,
        // which is why the seed showed up at the beginning of every signal).
        let mut row = vec![0.0; 400];
        row[20..60].fill(2.0);
        row[399] = 2.4; // non-silent tail -> seed 0.1
        let (core, n_time) = core_from_rows(&[row]);
        let zero = nl_loudness_scalar(&core, n_time);
        let tail = nl_loudness_scalar_with(&core, n_time, NlInit::MosqitoTail);
        assert_eq!(zero[0], 0.0);
        assert!(tail[0] > 0.0 && tail[0] < 0.1, "decaying seed: {}", tail[0]);
        assert_eq!(zero[20], 2.0);
        assert_eq!(tail[20], 2.0);
    }

    #[cfg(target_arch = "x86_64")]
    #[test]
    fn avx2_and_scalar_agree_for_both_initialisations() {
        if !crate::simd::use_avx2() {
            return;
        }
        let rows: Vec<Vec<f64>> = (0..21)
            .map(|b| {
                (0..300)
                    .map(|t| ((t * (b + 3)) % 17) as f64 * 0.1 + if t > 250 { 0.0 } else { 0.5 })
                    .collect()
            })
            .collect();
        let (core, n_time) = core_from_rows(&rows);
        for init in [NlInit::Zero, NlInit::MosqitoTail] {
            let s = nl_loudness_scalar_with(&core, n_time, init);
            let a = unsafe { nl_loudness_avx2(&core, n_time, ParMode::Sequential, init) };
            for (i, (x, y)) in s.iter().zip(&a).enumerate() {
                assert!(
                    (x - y).abs() <= 1e-12 * x.abs().max(1.0),
                    "{init:?} [{i}] {x} vs {y}"
                );
            }
        }
    }
}
