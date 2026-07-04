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

pub fn third_octave_levels(sig: &[f64]) -> (Vec<f64>, usize) {
    third_octave_levels_scalar(sig)
}

pub fn time_axis(_sig_len: usize, n_time: usize) -> Vec<f64> {
    (0..n_time).map(|i| (i * DEC_FACTOR) as f64 / FS).collect()
}
