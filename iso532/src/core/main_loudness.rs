use crate::tables::{A0, DCB, DDF, DLL, LTQ, RAP};
use crate::{FieldType, Iso532Error};
use rayon::prelude::*;

pub fn main_loudness(spec_third: &[f64], field: FieldType) -> Result<[f64; 21], Iso532Error> {
    assert_eq!(
        spec_third.len(),
        28,
        "main_loudness expects 28 third-octave band levels"
    );

    if spec_third[..11].iter().any(|&level| level > 120.0) {
        return Err(Iso532Error::LevelExceeds120dB);
    }

    let mut ti = [0.0; 11];
    for band in 0..11 {
        let mut dll_result = DLL[0][band];
        let mut previous = spec_third[band] > RAP[0] - DLL[0][band];
        if previous {
            dll_result = 0.0;
        }

        for range in 1..(DLL.len() - 1) {
            let current = spec_third[band] > RAP[range] - DLL[range][band];
            if previous ^ current {
                dll_result = DLL[range][band];
            }
            previous = current;
        }

        let xp = spec_third[band] + dll_result;
        ti[band] = 10.0_f64.powf(xp / 10.0);
    }

    let mut lcb = [0.0; 3];
    let gi = [
        ti[0..6].iter().sum::<f64>(),
        ti[6..9].iter().sum::<f64>(),
        ti[9..11].iter().sum::<f64>(),
    ];
    for (idx, energy) in gi.into_iter().enumerate() {
        if energy > 0.0 {
            lcb[idx] = 10.0 * energy.log10();
        }
    }

    let mut nm = [0.0; 21];
    for band in 0..20 {
        let mut le = spec_third[band + 8];
        if band < 3 {
            le = lcb[band];
        }

        le -= A0[band];
        if field == FieldType::Diffuse {
            le += DDF[band];
        }

        if le > LTQ[band] {
            le -= DCB[band];
            let mp1 = 0.0635 * 10.0_f64.powf(0.025 * LTQ[band]);
            let mp2 = (1.0 - 0.25 + 0.25 * 10.0_f64.powf(0.1 * (le - LTQ[band]))).powf(0.25) - 1.0;
            nm[band] = (mp1 * mp2).max(0.0);
        }
    }

    let korry = 0.4 + 0.32 * nm[0].powf(0.2);
    if korry <= 1.0 {
        nm[0] *= korry;
    }

    Ok(nm)
}
pub fn main_loudness_frames_into(
    frames: &[f64],
    n_time: usize,
    field: FieldType,
    core: &mut [f64],
) -> Result<(), Iso532Error> {
    assert_eq!(
        frames.len(),
        28 * n_time,
        "main_loudness_frames_into expects frame-major (n_time, 28) levels"
    );
    assert_eq!(
        core.len(),
        21 * n_time,
        "main_loudness_frames_into expects band-major (21, n_time) output"
    );

    let per_frame = frames
        .par_chunks_exact(28)
        .map(|frame| main_loudness(frame, field))
        .collect::<Result<Vec<_>, _>>()?;

    for (t, nm) in per_frame.iter().enumerate() {
        for band in 0..21 {
            core[band * n_time + t] = nm[band];
        }
    }

    Ok(())
}
#[cfg(test)]
mod tests {
    use super::{main_loudness, main_loudness_frames_into};
    use crate::FieldType;

    #[test]
    fn frame_major_batch_matches_per_frame_main_loudness() {
        let n_time = 3;
        let mut frames = vec![0.0; 28 * n_time];
        for t in 0..n_time {
            for band in 0..28 {
                frames[t * 28 + band] = 35.0 + band as f64 * 0.75 + t as f64 * 1.25;
            }
        }
        let mut core = vec![f64::NAN; 21 * n_time];

        main_loudness_frames_into(&frames, n_time, FieldType::Free, &mut core).unwrap();

        for t in 0..n_time {
            let expected = main_loudness(&frames[t * 28..(t + 1) * 28], FieldType::Free).unwrap();
            for band in 0..21 {
                assert_eq!(
                    core[band * n_time + t],
                    expected[band],
                    "band {band} frame {t}"
                );
            }
        }
    }
}
