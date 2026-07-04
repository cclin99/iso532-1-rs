pub mod nonlinear_decay;
pub mod temporal_weighting;
pub mod third_octave_levels;

use crate::core::calc_slopes::{calc_slopes_into, calc_slopes_n_only};
use crate::core::main_loudness::main_loudness_frames_into;
use crate::zwst::bark_axis;
use crate::{FieldType, Iso532Error, LoudnessTimeVarying};
use rayon::prelude::*;

#[derive(Debug, Default)]
pub struct ZwtvProcessor {
    third_octave_frames: Vec<f64>,
    core: Vec<f64>,
    loudness: Vec<f64>,
    spec_time_major: Vec<f64>,
}

impl ZwtvProcessor {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn process(
        &mut self,
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
        self.third_octave_frames.resize(28 * n_time, 0.0);
        for t in 0..n_time {
            for band in 0..28 {
                self.third_octave_frames[t * 28 + band] = tol[band * n_time + t];
            }
        }

        self.core.resize(21 * n_time, 0.0);
        main_loudness_frames_into(&self.third_octave_frames, n_time, field, &mut self.core)?;

        let nl = nonlinear_decay::nl_loudness(&self.core, n_time);
        self.loudness.resize(n_time, 0.0);
        self.loudness
            .par_iter_mut()
            .enumerate()
            .for_each(|(t, loudness)| {
                let frame: [f64; 21] = std::array::from_fn(|band| nl[band * n_time + t]);
                *loudness = calc_slopes_n_only(&frame);
            });

        let n_out = n_time.div_ceil(4);
        self.spec_time_major.resize(240 * n_out, 0.0);
        self.spec_time_major
            .par_chunks_mut(240)
            .enumerate()
            .for_each(|(out_idx, spec)| {
                let t = out_idx * 4;
                let frame: [f64; 21] = std::array::from_fn(|band| nl[band * n_time + t]);
                calc_slopes_into(&frame, spec);
            });

        let filt = temporal_weighting::temporal_weighting(&self.loudness);
        let time_axis = third_octave_levels::time_axis(signal.len(), n_time);
        let mut n = Vec::with_capacity(n_out);
        let mut out_time = Vec::with_capacity(n_out);
        for t in (0..n_time).step_by(4) {
            n.push(filt[t]);
            out_time.push(time_axis[t]);
        }

        let mut n_specific = Vec::with_capacity(240 * n.len());
        for bark in 0..240 {
            for out_idx in 0..n.len() {
                n_specific.push(self.spec_time_major[out_idx * 240 + bark]);
            }
        }

        Ok(LoudnessTimeVarying {
            n,
            n_specific,
            bark_axis: bark_axis(),
            time_axis: out_time,
        })
    }

    #[cfg(test)]
    fn scratch_capacities(&self) -> (usize, usize, usize, usize) {
        (
            self.third_octave_frames.capacity(),
            self.core.capacity(),
            self.loudness.capacity(),
            self.spec_time_major.capacity(),
        )
    }
}

pub fn loudness_zwtv(
    signal: &[f64],
    fs: f64,
    field: FieldType,
) -> Result<LoudnessTimeVarying, Iso532Error> {
    ZwtvProcessor::new().process(signal, fs, field)
}
#[cfg(test)]
mod tests {
    use super::{loudness_zwtv, ZwtvProcessor};
    use crate::FieldType;

    #[test]
    fn processor_matches_free_function_and_reuses_scratch_capacity() {
        let signal: Vec<f64> = (0..48_000)
            .map(|i| (2.0 * std::f64::consts::PI * 1_000.0 * i as f64 / 48_000.0).sin() * 0.02)
            .collect();
        let mut processor = ZwtvProcessor::new();

        let first = processor
            .process(&signal, 48_000.0, FieldType::Free)
            .unwrap();
        let capacities = processor.scratch_capacities();
        let second = processor
            .process(&signal, 48_000.0, FieldType::Free)
            .unwrap();
        let expected = loudness_zwtv(&signal, 48_000.0, FieldType::Free).unwrap();

        assert_eq!(processor.scratch_capacities(), capacities);
        assert_eq!(second.n, first.n);
        assert_eq!(second.n_specific, first.n_specific);
        assert_eq!(second.n, expected.n);
        assert_eq!(second.n_specific, expected.n_specific);
    }
}
