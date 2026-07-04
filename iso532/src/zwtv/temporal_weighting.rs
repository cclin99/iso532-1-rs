const LP_ITER: usize = 24;
const SAMPLE_RATE: f64 = 2000.0;

fn lowpass_intp(loudness: &[f64], tau: f64) -> Vec<f64> {
    let a1 = (-1.0 / (SAMPLE_RATE * LP_ITER as f64 * tau)).exp();
    let b0 = 1.0 - a1;
    let mut out = vec![0.0; loudness.len()];
    let mut y = 0.0;

    for t in 0..loudness.len() {
        let next = if t + 1 < loudness.len() {
            loudness[t + 1]
        } else {
            0.0
        };
        let delta = (next - loudness[t]) / LP_ITER as f64;
        for k in 0..LP_ITER {
            let ui = loudness[t] + delta * k as f64;
            y = b0 * ui + a1 * y;
            if k == 0 {
                out[t] = y;
            }
        }
    }

    out
}

/// Duration-dependent loudness perception: 0.47*LP(3.5ms) + 0.53*LP(70ms).
pub fn temporal_weighting(loudness: &[f64]) -> Vec<f64> {
    let fast = lowpass_intp(loudness, 3.5e-3);
    let slow = lowpass_intp(loudness, 70e-3);
    fast.iter()
        .zip(slow)
        .map(|(f, s)| 0.47 * f + 0.53 * s)
        .collect()
}
