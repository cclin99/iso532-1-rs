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
    Ok(main_loudness_unchecked(spec_third, field))
}

/// ISO 532-1 Annex A `corr_third_octave_intensities` row selection: the first
/// RAP range whose threshold `RAP[j] - DLL[j][band]` the level does not exceed,
/// saturating at the last row. The comparison is strict, so a level exactly on
/// a threshold stays in the lower row.
///
/// MoSQITo 1.2.1 vectorises this loop as `arange(1, 7)` and never reaches the
/// last row, which leaves a 0 dB correction above the seventh threshold (for
/// example > 118 dB on the 25 Hz band). That is an upstream implementation
/// slip, not a design choice; this crate follows Annex A (F-01, see
/// docs/F01-LOW-FREQ-DLL-ROW-FIX-2026-10-31.md).
#[inline]
pub(crate) fn low_freq_dll_row(level: f64, band: usize) -> usize {
    let last = DLL.len() - 1;
    let mut row = 0;
    while row < last && level > RAP[row] - DLL[row][band] {
        row += 1;
    }
    row
}

fn main_loudness_unchecked(spec_third: &[f64], field: FieldType) -> [f64; 21] {
    let mut ti = [0.0; 11];
    for band in 0..11 {
        let row = low_freq_dll_row(spec_third[band], band);
        let xp = spec_third[band] + DLL[row][band];
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

    nm
}

pub(crate) fn main_loudness_clamped(spec_third: &[f64; 28], field: FieldType) -> ([f64; 21], bool) {
    let mut frame = *spec_third;
    let mut clamped = false;
    for level in &mut frame[..11] {
        if *level > 120.0 {
            *level = 120.0;
            clamped = true;
        }
    }
    (main_loudness_unchecked(&frame, field), clamped)
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
    use super::{
        low_freq_dll_row, main_loudness, main_loudness_clamped, main_loudness_frames_into,
    };
    use crate::tables::{DLL, RAP};
    use crate::FieldType;

    fn threshold(row: usize, band: usize) -> f64 {
        RAP[row] - DLL[row][band]
    }

    #[test]
    fn low_freq_thresholds_are_strictly_increasing_per_band() {
        // Annex A's while loop assumes the ranges are ordered; pin the table.
        for band in 0..11 {
            for row in 1..DLL.len() {
                assert!(
                    threshold(row, band) > threshold(row - 1, band),
                    "band {band}: threshold row {row} not above row {}",
                    row - 1
                );
            }
        }
    }

    #[test]
    fn low_freq_dll_row_matches_annex_a_at_every_threshold() {
        let last = DLL.len() - 1;
        for band in 0..11 {
            for row in 0..DLL.len() {
                let thr = threshold(row, band);
                assert_eq!(
                    low_freq_dll_row(thr.next_down(), band),
                    row,
                    "band {band} just below threshold {row}"
                );
                assert_eq!(
                    low_freq_dll_row(thr, band),
                    row,
                    "band {band} exactly on threshold {row} (strict compare)"
                );
                assert_eq!(
                    low_freq_dll_row(thr.next_up(), band),
                    (row + 1).min(last),
                    "band {band} just above threshold {row}"
                );
            }
            assert_eq!(low_freq_dll_row(-1000.0, band), 0, "band {band} floor");
            assert_eq!(low_freq_dll_row(1000.0, band), last, "band {band} ceiling");
            assert_eq!(low_freq_dll_row(f64::NAN, band), 0, "band {band} NaN");
        }
    }

    #[test]
    fn low_freq_last_row_is_reachable_below_120_db() {
        // Every band whose seventh threshold is below the 120 dB validity
        // limit must reach the last row inside the accepted input domain.
        // (MoSQITo 1.2.1 never selects it; see F-01.)
        let last = DLL.len() - 1;
        for band in 0..11 {
            let thr = threshold(last - 1, band);
            if thr < 120.0 {
                assert_eq!(low_freq_dll_row(120.0, band), last, "band {band} at 120 dB");
            }
        }
        // band 0: 118 dB -> row 6 (-18 dB), 118 + ULP -> row 7 (-15 dB)
        assert_eq!(threshold(6, 0), 118.0);
        assert_eq!(DLL[low_freq_dll_row(118.0, 0)][0], -18.0);
        assert_eq!(DLL[low_freq_dll_row(118.0_f64.next_up(), 0)][0], -15.0);
    }

    #[test]
    fn clamped_variant_shares_the_row_selection_below_the_clamp() {
        let mut frame = [-60.0; 28];
        frame[0] = 119.0;
        let (clamped_nm, clamped) = main_loudness_clamped(&frame, FieldType::Free);
        assert!(!clamped);
        assert_eq!(clamped_nm, main_loudness(&frame, FieldType::Free).unwrap());
    }

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

    #[test]
    fn clamped_variant_flags_and_matches_at_120() {
        let mut frame = [60.0; 28];
        frame[3] = 130.0;
        let (nm, clamped) = main_loudness_clamped(&frame, FieldType::Free);
        assert!(clamped);
        let mut at_limit = frame;
        at_limit[3] = 120.0;
        assert_eq!(nm, main_loudness(&at_limit, FieldType::Free).unwrap());
        let (_, ok) = main_loudness_clamped(&[60.0; 28], FieldType::Free);
        assert!(!ok);
    }
}
