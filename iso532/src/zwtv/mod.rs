pub mod nonlinear_decay;
pub mod stream;
pub mod temporal_weighting;
pub mod third_octave_levels;

use crate::core::calc_slopes::{calc_slopes_into, calc_slopes_n_only};
use crate::core::main_loudness::main_loudness_frames_into;
use crate::zwst::bark_axis;
use crate::{FieldType, Iso532Error, LoudnessTimeVarying};
use rayon::prelude::*;

/// 輸出格線相對 third-octave 框架的再抽取因子(2 ms 格線)。
pub(crate) const OUT_DECIM: usize = 4;

/// `loudness_zwtv` 對 `signal_len` 樣本輸入的輸出框架數。
/// 純函數、不驗證輸入；binding 必須轉發本函式，勿手抄公式。
pub fn zwtv_out_frames(signal_len: usize) -> usize {
    signal_len
        .div_ceil(third_octave_levels::DEC_FACTOR)
        .div_ceil(OUT_DECIM)
}

/// 頻帶平行階段的排程模式。離線批次走 `Rayon`;
/// R5 串流路徑必須選 `Sequential`(音訊路徑不得觸發 thread pool)。
/// 注意:scalar 後備路徑在 `Rayon` 模式下的暫態配置隨執行緒數放大
/// (10 s 訊號 @12 緒:tol ~46 MB、nl ~138 MB),僅限離線批次使用。
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ParMode {
    Rayon,
    Sequential,
}

pub(crate) fn chunks_dispatch<F>(out: &mut [f64], chunk: usize, mode: ParMode, f: F)
where
    F: Fn(usize, &mut [f64]) + Sync,
{
    if out.is_empty() {
        return;
    }
    match mode {
        ParMode::Rayon => out
            .par_chunks_mut(chunk)
            .enumerate()
            .for_each(|(index, piece)| f(index, piece)),
        ParMode::Sequential => {
            for (index, piece) in out.chunks_mut(chunk).enumerate() {
                f(index, piece);
            }
        }
    }
}

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
        let n_out = n_time.div_ceil(OUT_DECIM);
        self.loudness.resize(n_time, 0.0);
        self.spec_time_major.resize(240 * n_out, 0.0);
        self.loudness
            .par_chunks_mut(OUT_DECIM)
            .zip_eq(self.spec_time_major.par_chunks_mut(240))
            .enumerate()
            .for_each(|(out_idx, (loudness_chunk, spec))| {
                let t0 = out_idx * OUT_DECIM;
                let frame: [f64; 21] = std::array::from_fn(|band| nl[band * n_time + t0]);
                loudness_chunk[0] = calc_slopes_into(&frame, spec);
                for (offset, loudness) in loudness_chunk.iter_mut().enumerate().skip(1) {
                    let frame: [f64; 21] =
                        std::array::from_fn(|band| nl[band * n_time + (t0 + offset)]);
                    *loudness = calc_slopes_n_only(&frame);
                }
            });

        let filt = temporal_weighting::temporal_weighting(&self.loudness);
        let time_axis = third_octave_levels::time_axis(signal.len(), n_time);
        let mut n = Vec::with_capacity(n_out);
        let mut out_time = Vec::with_capacity(n_out);
        for t in (0..n_time).step_by(OUT_DECIM) {
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
    fn zwtv_out_frames_matches_pipeline_output() {
        let signal: Vec<f64> = (0..48_000)
            .map(|i| (i % 480) as f64 / 480.0 * 0.02 - 0.01)
            .collect();
        for len in [4800usize, 4801, 4823, 4824, 4895, 4896, 4897, 48_000] {
            let n = loudness_zwtv(&signal[..len], 48_000.0, FieldType::Free)
                .unwrap()
                .n
                .len();
            assert_eq!(super::zwtv_out_frames(len), n, "len={len}");
        }
    }

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
