pub mod nonlinear_decay;
pub mod temporal_weighting;
pub mod third_octave_levels;

use crate::core::calc_slopes::calc_slopes;
use crate::core::main_loudness::main_loudness;
use crate::zwst::bark_axis;
use crate::{FieldType, Iso532Error, LoudnessTimeVarying};

pub fn loudness_zwtv(
    signal: &[f64],
    fs: f64,
    field: FieldType,
) -> Result<LoudnessTimeVarying, Iso532Error> {
    if fs != 48000.0 {
        return Err(Iso532Error::UnsupportedSampleRate(fs));
    }
    if signal.len() < 4800 {
        return Err(Iso532Error::SignalTooShort {
            got: signal.len(),
            need: 4800,
        });
    }

    let (tol, n_time) = third_octave_levels::third_octave_levels(signal);
    let mut core = vec![0.0; 21 * n_time];
    for t in 0..n_time {
        let frame: [f64; 28] = std::array::from_fn(|band| tol[band * n_time + t]);
        let nm = main_loudness(&frame, field)?;
        for band in 0..21 {
            core[band * n_time + t] = nm[band];
        }
    }

    let nl = nonlinear_decay::nl_loudness(&core, n_time);
    let mut loudness = vec![0.0; n_time];
    let mut spec_loudness = vec![0.0; 240 * n_time];
    for t in 0..n_time {
        let frame: [f64; 21] = std::array::from_fn(|band| nl[band * n_time + t]);
        let (n, spec) = calc_slopes(&frame);
        loudness[t] = n;
        for bark in 0..240 {
            spec_loudness[bark * n_time + t] = spec[bark];
        }
    }

    let filt = temporal_weighting::temporal_weighting(&loudness);
    let time_axis = third_octave_levels::time_axis(signal.len(), n_time);
    let n_out = n_time.div_ceil(4);
    let mut n = Vec::with_capacity(n_out);
    let mut out_time = Vec::with_capacity(n_out);
    for t in (0..n_time).step_by(4) {
        n.push(filt[t]);
        out_time.push(time_axis[t]);
    }

    let mut n_specific = Vec::with_capacity(240 * n.len());
    for bark in 0..240 {
        for t in (0..n_time).step_by(4) {
            n_specific.push(spec_loudness[bark * n_time + t]);
        }
    }

    Ok(LoudnessTimeVarying {
        n,
        n_specific,
        bark_axis: bark_axis(),
        time_axis: out_time,
    })
}
