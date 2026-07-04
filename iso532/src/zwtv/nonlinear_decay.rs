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
    assert_eq!(
        core.len(),
        21 * n_time,
        "nl_loudness expects row-major (21, n_time) core loudness"
    );

    let b = nl_coeffs();
    let mut out = vec![0.0; core.len()];

    for band in 0..21 {
        let row = &core[band * n_time..(band + 1) * n_time];
        let out_row = &mut out[band * n_time..(band + 1) * n_time];
        nl_loudness_band_scalar(row, out_row, &b);
    }

    out
}

fn nl_loudness_band_scalar(row: &[f64], out: &mut [f64], b: &[f64; 6]) {
    let n_time = row.len();
    assert_eq!(out.len(), n_time);
    if n_time == 0 {
        return;
    }

    let n_inner = n_time * NL_ITER;
    let mut ui_delta = vec![0.0; n_inner];
    for t in 0..n_time {
        let next = if t + 1 < n_time { row[t + 1] } else { 0.0 };
        let delta = (next - row[t]) / NL_ITER as f64;
        for k in 0..NL_ITER {
            ui_delta[t * NL_ITER + k] = row[t] + delta * k as f64;
        }
    }

    // Mosqito initializes uo from ui_delta. The col=0 loop intentionally
    // reads col-1, so the previous uo is the final virtual substep.
    let mut uo = ui_delta.clone();
    let mut u2 = vec![0.0; n_inner];
    if row[0] >= 1e-5 {
        u2[0] = row[0] * (1.0 - b[5]);
    }

    for col in 0..n_inner {
        let prev = if col == 0 { n_inner - 1 } else { col - 1 };
        let ui = ui_delta[col];

        let uo2 = uo[prev] * b[2] - u2[prev] * b[3];
        if uo[prev] > u2[prev] && uo2 >= ui {
            uo[col] = uo2;
        }

        let uo2 = uo[prev] * b[4];
        if uo[prev] <= u2[prev] && uo2 >= ui {
            uo[col] = uo2;
        }

        u2[col] = uo[col];

        let u22 = uo[prev] * b[0] - u2[prev] * b[1];
        if ui < uo[prev] && uo[prev] > u2[prev] && u22 <= uo[col] {
            u2[col] = u22;
        }

        let u2_2 = (u2[prev] - ui) * b[5] + ui;
        if ui >= uo[prev] && !((ui - uo[prev]).abs() < 1e-5 && uo[col] <= u2[prev]) {
            u2[col] = u2_2;
        }
    }

    for t in 0..n_time {
        out[t] = uo[t * NL_ITER];
    }
}

/// AVX2+FMA nonlinear temporal decay kernel.
///
/// # Safety
/// Caller must ensure AVX2 and FMA are available before calling.
#[cfg(target_arch = "x86_64")]
#[target_feature(enable = "avx2,fma")]
pub unsafe fn nl_loudness_avx2(core: &[f64], n_time: usize) -> Vec<f64> {
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

    for band in (0..20).step_by(4) {
        nl_loudness_process4(core, &mut out, n_time, band, b);
    }

    nl_loudness_band_scalar(
        &core[20 * n_time..21 * n_time],
        &mut out[20 * n_time..21 * n_time],
        &b,
    );

    out
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
#[target_feature(enable = "avx2,fma")]
unsafe fn nl_loudness_process4(
    core: &[f64],
    out: &mut [f64],
    n_time: usize,
    band: usize,
    b: [f64; 6],
) {
    use std::arch::x86_64::*;

    let b0 = _mm256_set1_pd(b[0]);
    let b1 = _mm256_set1_pd(b[1]);
    let b2 = _mm256_set1_pd(b[2]);
    let b3 = _mm256_set1_pd(b[3]);
    let b4 = _mm256_set1_pd(b[4]);
    let b5 = _mm256_set1_pd(b[5]);
    let inv_iter = _mm256_set1_pd(1.0 / NL_ITER as f64);
    let eps = _mm256_set1_pd(1e-5);

    let last = n_time - 1;
    let last_row = nl_loudness_load4(core, n_time, band, last);
    let last_delta = _mm256_mul_pd(_mm256_sub_pd(_mm256_setzero_pd(), last_row), inv_iter);
    let mut prev_uo = _mm256_fmadd_pd(last_delta, _mm256_set1_pd((NL_ITER - 1) as f64), last_row);
    let mut prev_u2 = _mm256_setzero_pd();

    for t in 0..n_time {
        let row = nl_loudness_load4(core, n_time, band, t);
        let next = if t + 1 < n_time {
            nl_loudness_load4(core, n_time, band, t + 1)
        } else {
            _mm256_setzero_pd()
        };
        let delta = _mm256_mul_pd(_mm256_sub_pd(next, row), inv_iter);

        for k in 0..NL_ITER {
            let ui = _mm256_fmadd_pd(delta, _mm256_set1_pd(k as f64), row);

            let mut uo = ui;
            let uo2_fast = _mm256_fnmadd_pd(prev_u2, b3, _mm256_mul_pd(prev_uo, b2));
            let mask_fast = _mm256_and_pd(
                _mm256_cmp_pd(prev_uo, prev_u2, _CMP_GT_OQ),
                _mm256_cmp_pd(uo2_fast, ui, _CMP_GE_OQ),
            );
            uo = _mm256_blendv_pd(uo, uo2_fast, mask_fast);

            let uo2_slow = _mm256_mul_pd(prev_uo, b4);
            let mask_slow = _mm256_and_pd(
                _mm256_cmp_pd(prev_uo, prev_u2, _CMP_LE_OQ),
                _mm256_cmp_pd(uo2_slow, ui, _CMP_GE_OQ),
            );
            uo = _mm256_blendv_pd(uo, uo2_slow, mask_slow);

            let mut u2 = uo;
            let u22 = _mm256_fnmadd_pd(prev_u2, b1, _mm256_mul_pd(prev_uo, b0));
            let mask_u22 = _mm256_and_pd(
                _mm256_and_pd(
                    _mm256_cmp_pd(ui, prev_uo, _CMP_LT_OQ),
                    _mm256_cmp_pd(prev_uo, prev_u2, _CMP_GT_OQ),
                ),
                _mm256_cmp_pd(u22, uo, _CMP_LE_OQ),
            );
            u2 = _mm256_blendv_pd(u2, u22, mask_u22);

            let u2_2 = _mm256_fmadd_pd(_mm256_sub_pd(prev_u2, ui), b5, ui);
            let diff_abs = _mm256_andnot_pd(_mm256_set1_pd(-0.0), _mm256_sub_pd(ui, prev_uo));
            let near_and_not_higher = _mm256_and_pd(
                _mm256_cmp_pd(diff_abs, eps, _CMP_LT_OQ),
                _mm256_cmp_pd(uo, prev_u2, _CMP_LE_OQ),
            );
            let mask_u2_2 =
                _mm256_andnot_pd(near_and_not_higher, _mm256_cmp_pd(ui, prev_uo, _CMP_GE_OQ));
            u2 = _mm256_blendv_pd(u2, u2_2, mask_u2_2);

            if k == 0 {
                let mut lanes = [0.0; 4];
                _mm256_storeu_pd(lanes.as_mut_ptr(), uo);
                for lane in 0..4 {
                    out[(band + lane) * n_time + t] = lanes[lane];
                }
            }

            prev_uo = uo;
            prev_u2 = u2;
        }
    }
}

pub fn nl_loudness(core: &[f64], n_time: usize) -> Vec<f64> {
    #[cfg(target_arch = "x86_64")]
    {
        if crate::simd::use_avx2() {
            return unsafe { nl_loudness_avx2(core, n_time) };
        }
    }
    nl_loudness_scalar(core, n_time)
}
