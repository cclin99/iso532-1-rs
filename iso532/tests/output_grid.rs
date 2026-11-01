//! C-01 output-grid contract (decision 2026-11-01: keep ceil).
//!
//! Contract under test, for a signal of `L` samples at 48 kHz:
//! - internal 2 kHz frames: `ceil(L/24)`, frame `t` sampled at sample `24t`;
//! - output points: `frames = ceil(ceil(L/24)/4)`, point `j` is internal frame `4j`,
//!   `time_axis[j] = 96j / 48000` exactly, starting at 0;
//! - the value of point `j` depends only on samples `<= 96j` (prefix-determined);
//! - the stream produces the same number of frames as the batch for any chunking;
//! - the official CLI grids are prefixes: total `floor(K/4)`, specific `ceil(K/4)`,
//!   `K = floor(L/24)`; each is `frames` or `frames - 1`.
mod common;

use common::{run_chunked, synth_signal};
use iso532::{loudness_zwtv, zwtv_out_frames, FieldType, Iso532Error};

const FS: f64 = 48_000.0;
const DEC: usize = 24;
const OUT_DECIM: usize = 4;

/// Lengths covering every case of the memo: shortest legal, `24k ± 1`, `96k ± 1`,
/// `K mod 4 = 0` with `r > 0` (47905, 47916, 47927), `K mod 4 != 0` (47928..47999),
/// and multiples of 96.
const LENGTHS: [usize; 16] = [
    4800, 4801, 4823, 4824, 4825, 4895, 4896, 4897, 24_013, 47_905, 47_916, 47_927, 47_928, 47_952,
    47_999, 48_000,
];

fn expected_frames(len: usize) -> usize {
    len.div_ceil(DEC).div_ceil(OUT_DECIM)
}

fn cli_total(len: usize) -> usize {
    (len / DEC) / OUT_DECIM
}

fn cli_specific(len: usize) -> usize {
    (len / DEC).div_ceil(OUT_DECIM)
}

#[test]
fn frame_count_is_ceil_of_ceil_for_every_field() {
    let signal = synth_signal();
    for &len in &LENGTHS {
        let want = expected_frames(len);
        assert_eq!(zwtv_out_frames(len), want, "zwtv_out_frames({len})");
        let r = loudness_zwtv(&signal[..len], FS, FieldType::Free).unwrap();
        assert_eq!(r.n.len(), want, "n.len() for L={len}");
        assert_eq!(r.time_axis.len(), want, "time_axis.len() for L={len}");
        assert_eq!(
            r.n_specific.len(),
            240 * want,
            "n_specific.len() for L={len}"
        );
        assert_eq!(r.bark_axis.len(), 240, "bark_axis.len() for L={len}");
    }
}

#[test]
fn shortest_legal_input_is_4800_samples_and_50_points() {
    let signal = synth_signal();
    assert_eq!(expected_frames(4800), 50);
    assert_eq!(
        loudness_zwtv(&signal[..4800], FS, FieldType::Free)
            .unwrap()
            .n
            .len(),
        50
    );
    match loudness_zwtv(&signal[..4799], FS, FieldType::Free) {
        Err(Iso532Error::SignalTooShort { got, need }) => {
            assert_eq!((got, need), (4799, 4800));
        }
        other => panic!("expected SignalTooShort, got {other:?}"),
    }
}

#[test]
fn time_axis_is_an_exact_2ms_grid_from_zero() {
    let signal = synth_signal();
    for &len in &LENGTHS {
        let r = loudness_zwtv(&signal[..len], FS, FieldType::Free).unwrap();
        for (j, &t) in r.time_axis.iter().enumerate() {
            let want = (j * DEC * OUT_DECIM) as f64 / FS;
            assert_eq!(
                t.to_bits(),
                want.to_bits(),
                "time_axis[{j}] for L={len}: got {t:e}, want {want:e}"
            );
        }
        // The last point lies inside the signal: sample 96(frames-1) exists.
        let last = (r.n.len() - 1) * DEC * OUT_DECIM;
        assert!(
            last < len,
            "L={len}: last point at sample {last} is past the end"
        );
    }
}

#[test]
fn cli_grids_are_prefixes_of_the_rust_grid() {
    for &len in &LENGTHS {
        let frames = expected_frames(len);
        let total = cli_total(len);
        let specific = cli_specific(len);
        assert!(total <= specific && specific <= frames, "L={len}");
        assert!(
            frames - total <= 1,
            "L={len}: total differs by more than one point"
        );
        assert!(
            frames - specific <= 1,
            "L={len}: specific differs by more than one point"
        );
        let k = len / DEC;
        let r = len % DEC;
        if len.is_multiple_of(DEC * OUT_DECIM) {
            assert_eq!(
                (total, specific),
                (frames, frames),
                "L={len}: multiple of 96"
            );
        } else if !k.is_multiple_of(OUT_DECIM) {
            assert_eq!(
                specific, frames,
                "L={len}: K mod 4 != 0 matches CLI specific"
            );
            assert_eq!(total, frames - 1, "L={len}");
        } else {
            assert!(r > 0, "L={len}");
            assert_eq!(
                (total, specific),
                (frames - 1, frames - 1),
                "L={len}: K mod 4 = 0, r > 0"
            );
        }
    }
}

#[test]
fn stream_frame_count_equals_batch_for_any_chunking() {
    let signal = synth_signal();
    let mut random = 0x9e37_79b9_7f4a_7c15_u64;
    for &len in &LENGTHS {
        let want = expected_frames(len);
        for chunk in [1usize, 7, 24, 96, 480, 4800, len] {
            let frames = run_chunked(&signal[..len], std::iter::repeat(chunk));
            assert_eq!(frames.len(), want, "L={len}, chunk={chunk}");
            assert_eq!(
                frames.last().unwrap().t_frame_index,
                (want - 1) as u64,
                "L={len}, chunk={chunk}: last frame index"
            );
        }
        let sizes = std::iter::from_fn(move || {
            random ^= random << 13;
            random ^= random >> 7;
            random ^= random << 17;
            Some(1 + (random % 1000) as usize)
        });
        let frames = run_chunked(&signal[..len], sizes.take(10_000));
        assert_eq!(frames.len(), want, "L={len}, random chunking");
    }
}

fn assert_prefix_bitwise(
    short: &iso532::LoudnessTimeVarying,
    long: &iso532::LoudnessTimeVarying,
    ctx: &str,
) {
    let frames = short.n.len();
    assert!(long.n.len() >= frames, "{ctx}: longer run has fewer points");
    for j in 0..frames {
        assert_eq!(
            short.n[j].to_bits(),
            long.n[j].to_bits(),
            "{ctx}: n[{j}] differs ({:e} vs {:e})",
            short.n[j],
            long.n[j]
        );
        assert_eq!(
            short.time_axis[j].to_bits(),
            long.time_axis[j].to_bits(),
            "{ctx}: time[{j}]"
        );
    }
    let long_frames = long.n.len();
    for bark in 0..240 {
        for j in 0..frames {
            let s = short.n_specific[bark * frames + j];
            let l = long.n_specific[bark * long_frames + j];
            assert_eq!(
                s.to_bits(),
                l.to_bits(),
                "{ctx}: n_specific[{bark}][{j}] ({s:e} vs {l:e})"
            );
        }
    }
}

/// The §2.2 probe as a test: truncating at `L` and zero-padding beyond `L` give the
/// same points, including the trailing one that the official C library skips.
#[test]
fn every_point_is_prefix_determined_under_zero_padding() {
    let signal = synth_signal();
    for &len in &LENGTHS {
        let short = loudness_zwtv(&signal[..len], FS, FieldType::Free).unwrap();
        let mut padded = signal[..len].to_vec();
        padded.resize(
            len.next_multiple_of(DEC * OUT_DECIM) + 3 * DEC * OUT_DECIM,
            0.0,
        );
        let long = loudness_zwtv(&padded, FS, FieldType::Free).unwrap();
        assert_prefix_bitwise(&short, &long, &format!("L={len}, zero-padded"));
    }
}

/// Stronger form: point `j` depends only on samples `<= 96j`, so the real continuation
/// of the signal does not change any point either.
#[test]
fn every_point_is_prefix_determined_under_real_continuation() {
    let signal = synth_signal();
    let full = loudness_zwtv(&signal, FS, FieldType::Free).unwrap();
    for &len in &LENGTHS {
        if len == signal.len() {
            continue;
        }
        let short = loudness_zwtv(&signal[..len], FS, FieldType::Free).unwrap();
        assert_prefix_bitwise(&short, &full, &format!("L={len}, real continuation"));
    }
}
