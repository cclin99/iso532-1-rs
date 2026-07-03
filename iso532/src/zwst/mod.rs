use crate::core::calc_slopes::calc_slopes;
use crate::core::main_loudness::main_loudness;
use crate::dsp::filtfilt::decimate;
use crate::dsp::sos::sosfilt;
use crate::tables_noct::{NOCT_DECIM_Q, NOCT_SOS};
use crate::{FieldType, Iso532Error, LoudnessStationary};

/// 1/3-octave band RMS amplitudes, 28 bands (24 Hz..12.6 kHz), fs = 48 kHz.
/// Mirrors mosqito noct_spectrum for a single-channel stationary signal.
pub fn noct_spectrum_rms(signal: &[f64]) -> Vec<f64> {
    (0..28)
        .map(|band| {
            let q = NOCT_DECIM_Q[band];
            let mut x = if q > 1 {
                decimate(signal, q)
            } else {
                signal.to_vec()
            };
            sosfilt(&NOCT_SOS[band], &mut x);
            let ms = x.iter().map(|v| v * v).sum::<f64>() / x.len() as f64;
            ms.sqrt()
        })
        .collect()
}

/// Convert pressure amplitudes to dB SPL with ref 2e-5, matching mosqito amp2db.
pub fn spec_to_db(spec: &[f64]) -> Vec<f64> {
    spec.iter()
        .map(|&a| {
            let a = if a == 0.0 { 2e-12 } else { a };
            20.0 * (a / 2e-5).log10()
        })
        .collect()
}

pub fn loudness_zwst(
    signal: &[f64],
    fs: f64,
    field: FieldType,
) -> Result<LoudnessStationary, Iso532Error> {
    if fs != 48000.0 {
        return Err(Iso532Error::UnsupportedSampleRate(fs));
    }
    if signal.len() < 4800 {
        return Err(Iso532Error::SignalTooShort {
            got: signal.len(),
            need: 4800,
        });
    }
    let spec = noct_spectrum_rms(signal);
    let spec_db = spec_to_db(&spec);
    let nm = main_loudness(&spec_db, field)?;
    let (n, n_specific) = calc_slopes(&nm);
    Ok(LoudnessStationary {
        n,
        n_specific: n_specific.to_vec(),
        bark_axis: bark_axis(),
    })
}

pub(crate) fn bark_axis() -> Vec<f64> {
    (0..240)
        .map(|i| 0.1 + (24.0 - 0.1) * i as f64 / 239.0)
        .collect()
}
