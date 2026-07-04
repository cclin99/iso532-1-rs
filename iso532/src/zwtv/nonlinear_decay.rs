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
    let n_inner = n_time * NL_ITER;
    let mut out = vec![0.0; core.len()];

    for band in 0..21 {
        let row = &core[band * n_time..(band + 1) * n_time];
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
            out[band * n_time + t] = uo[t * NL_ITER];
        }
    }

    out
}

pub fn nl_loudness(core: &[f64], n_time: usize) -> Vec<f64> {
    nl_loudness_scalar(core, n_time)
}
