mod common;

use common::run_chunked;
use iso532::{FieldType, FrameFlags, StreamFrame, ZwtvStream, N_WARMUP_FRAMES};

fn assert_frames_bitwise(got: &[StreamFrame], expected: &[StreamFrame], ctx: &str) {
    assert_eq!(got.len(), expected.len(), "{ctx}: length");
    for (i, (actual, expected)) in got.iter().zip(expected).enumerate() {
        assert_eq!(
            actual.n.to_bits(),
            expected.n.to_bits(),
            "{ctx} frame={i}: n"
        );
        assert_eq!(
            actual.n_phon.to_bits(),
            expected.n_phon.to_bits(),
            "{ctx} frame={i}: n_phon"
        );
        assert_eq!(
            actual.t_frame_index, expected.t_frame_index,
            "{ctx} frame={i}: t_frame_index"
        );
        assert_eq!(actual.flags, expected.flags, "{ctx} frame={i}: flags");
    }
}

#[test]
fn stream_constants_and_single_push_reference() {
    assert_eq!(ZwtvStream::latency_samples(), 24);
    let signal = common::synth_signal();
    let reference = iso532::zwtv::stream::zwtv_reference_zerostate(&signal, FieldType::Free);
    let got = run_chunked(&signal, std::iter::once(signal.len()));
    assert_eq!(got.len(), reference.len());
    for (i, (frame, expected)) in got.iter().zip(reference).enumerate() {
        assert_eq!(frame.n.to_bits(), expected.to_bits(), "frame {i}");
        assert_eq!(frame.t_frame_index, i as u64);
        assert_eq!(frame.n_phon.to_bits(), iso532::sone2phon(frame.n).to_bits());
        assert_eq!(
            frame.flags.contains(FrameFlags::WARMUP),
            (i as u64) < N_WARMUP_FRAMES
        );
    }
}

#[test]
fn warmup_constant_is_frozen() {
    assert_eq!(N_WARMUP_FRAMES, 580);
}

#[test]
fn chunk_size_invariance_is_bitwise() {
    let signal = common::synth_signal();
    let baseline = run_chunked(&signal, std::iter::once(signal.len()));
    for &size in &[1usize, 7, 24, 64, 480, 4096] {
        let got = run_chunked(&signal, std::iter::repeat(size));
        assert_frames_bitwise(&got, &baseline, &format!("chunk={size}"));
    }
    let mut lcg = 0x9e37_79b9_7f4a_7c15_u64;
    let random = std::iter::from_fn(move || {
        lcg = lcg
            .wrapping_mul(6_364_136_223_846_793_005)
            .wrapping_add(1_442_695_040_888_963_407);
        Some(1 + (lcg >> 33) as usize % 997)
    });
    assert_frames_bitwise(
        &run_chunked(&signal, random.take(10_000)),
        &baseline,
        "random-LCG",
    );
}

#[test]
fn reset_matches_a_new_stream() {
    let signal = common::synth_signal();
    let expected = run_chunked(&signal, std::iter::repeat(480));
    let mut stream = ZwtvStream::new(FieldType::Free);
    let mut out = vec![StreamFrame::default(); 64];
    let _ = stream.push(&signal[..4800], &mut out);
    stream.reset();
    let mut got = Vec::new();
    for chunk in signal.chunks(480) {
        let n = stream.push(chunk, &mut out);
        got.extend_from_slice(&out[..n]);
    }
    let n = stream.flush(&mut out);
    got.extend_from_slice(&out[..n]);
    assert_frames_bitwise(&got, &expected, "reset");
}

#[test]
fn flush_reset_after_partial_nonfinite_chunk_matches_a_new_stream() {
    let signal = common::synth_signal();
    let expected = run_chunked(&signal, std::iter::repeat(480));
    let mut dirty = signal[..481].to_vec();
    dirty[479] = f64::NAN;

    let mut stream = ZwtvStream::new(FieldType::Free);
    let mut out = vec![StreamFrame::default(); 64];
    let _ = stream.push(&dirty, &mut out);
    let _ = stream.flush(&mut out);
    stream.reset();

    let mut got = Vec::new();
    for chunk in signal.chunks(480) {
        let n = stream.push(chunk, &mut out);
        got.extend_from_slice(&out[..n]);
    }
    let n = stream.flush(&mut out);
    got.extend_from_slice(&out[..n]);
    assert_frames_bitwise(&got, &expected, "flush-reset-partial-nonfinite");
}

#[test]
fn zerostate_and_stream_converge_to_batch_after_warmup() {
    let one_second = common::synth_signal();
    let signal: Vec<f64> = one_second.iter().copied().cycle().take(144_000).collect();
    let batch = iso532::loudness_zwtv(&signal, 48_000.0, FieldType::Free).unwrap();
    let zero = iso532::zwtv::stream::zwtv_reference_zerostate(&signal, FieldType::Free);
    let stream = run_chunked(&signal, std::iter::repeat(480));
    assert_eq!(batch.n.len(), zero.len());
    assert_eq!(batch.n.len(), stream.len());
    let first_sustained = (0..batch.n.len()).find(|&start| {
        batch.n[start..]
            .iter()
            .zip(&zero[start..])
            .all(|(a, b)| (a - b).abs() <= 1e-9)
    });
    eprintln!("first sustained <=1e-9: {first_sustained:?}");
    assert!(first_sustained.is_some_and(|frame| frame <= N_WARMUP_FRAMES as usize));
    for i in N_WARMUP_FRAMES as usize..batch.n.len() {
        assert!(
            (batch.n[i] - zero[i]).abs() <= 1e-9,
            "zero frame {i}: batch={} zero={} diff={}",
            batch.n[i],
            zero[i],
            (batch.n[i] - zero[i]).abs()
        );
        assert!(
            (batch.n[i] - stream[i].n).abs() <= 1e-9,
            "stream frame {i}: batch={} stream={} diff={}",
            batch.n[i],
            stream[i].n,
            (batch.n[i] - stream[i].n).abs()
        );
    }
}

#[test]
fn nine_golden_signals_match_zerostate_and_converge_after_warmup() {
    const NAMES: [&str; 9] = [
        "sine_1k_60",
        "sine_250_80",
        "sine_4k_60",
        "white_60",
        "pulse_1k_70",
        "step_60_80",
        "annexb_sig3",
        "annexb_sig5",
        "annexb_sig10",
    ];
    for name in NAMES {
        let one_second = common::read_bin(name, "sig.bin");
        let signal: Vec<f64> = one_second
            .iter()
            .copied()
            .cycle()
            .take(one_second.len() * 3)
            .collect();
        let reference = iso532::zwtv::stream::zwtv_reference_zerostate(&signal, FieldType::Free);
        let frames = run_chunked(&signal, std::iter::repeat(480));
        assert_eq!(frames.len(), reference.len(), "{name}");
        for (index, (frame, expected)) in frames.iter().zip(&reference).enumerate() {
            assert_eq!(
                frame.n.to_bits(),
                expected.to_bits(),
                "{name} E2 frame {index}"
            );
        }
        let batch = iso532::loudness_zwtv(&signal, 48_000.0, FieldType::Free).unwrap();
        for (index, (batch_n, frame)) in batch
            .n
            .iter()
            .zip(&frames)
            .enumerate()
            .skip(N_WARMUP_FRAMES as usize)
        {
            assert!(
                (batch_n - frame.n).abs() <= 1e-9,
                "{name} E3 frame {index}: diff={}",
                (batch_n - frame.n).abs()
            );
        }
    }
}

#[test]
fn nonfinite_input_flags_and_recovers() {
    let one_second = common::synth_signal();
    let signal: Vec<f64> = one_second.iter().copied().cycle().take(96_000).collect();
    let mut dirty = signal.clone();
    dirty[4800..4848].fill(f64::NAN);
    let clean = run_chunked(&signal, std::iter::repeat(480));
    let dirty = run_chunked(&dirty, std::iter::repeat(480));
    assert!(dirty
        .iter()
        .any(|frame| frame.flags.contains(FrameFlags::NONFINITE_INPUT)));
    assert!(dirty.iter().all(|frame| frame.n.is_finite()));
    let mut compared = 0;
    // Measured recovery begins at frame 794; 800 keeps margin for libm drift.
    for (a, b) in clean.iter().zip(&dirty).skip(800) {
        assert!((a.n - b.n).abs() < 1e-9);
        compared += 1;
    }
    assert!(compared > 0, "recovery comparison must not be empty");
}

#[test]
fn tail_nonfinite_input_is_reported_as_residual_flag() {
    let mut signal = vec![0.0; 48_048];
    signal[48_030] = f64::NAN;
    let mut stream = ZwtvStream::new(FieldType::Free);
    let mut out = vec![StreamFrame::default(); ZwtvStream::max_frames_for_chunk(signal.len())];
    let written = stream.push(&signal, &mut out);
    assert_eq!(written, 501);
    assert!(out[..written]
        .iter()
        .all(|frame| !frame.flags.contains(FrameFlags::NONFINITE_INPUT)));
    assert_eq!(stream.flush(&mut out), 0);
    assert!(stream
        .residual_flags()
        .contains(FrameFlags::NONFINITE_INPUT));
}

#[test]
fn over_120db_is_clamped_and_stream_continues() {
    let mut signal = common::synth_signal();
    for (i, sample) in signal[9600..14400].iter_mut().enumerate() {
        *sample = 2000.0 * (2.0 * std::f64::consts::PI * 100.0 * i as f64 / 48_000.0).sin();
    }
    let frames = run_chunked(&signal, std::iter::repeat(480));
    assert!(frames
        .iter()
        .any(|frame| frame.flags.contains(FrameFlags::CLAMPED_120DB)));
    assert!(frames.iter().all(|frame| frame.n.is_finite()));
    assert!(iso532::loudness_zwtv(&signal, 48_000.0, FieldType::Free).is_err());
}

#[cfg(target_arch = "x86_64")]
#[test]
fn push_and_flush_restore_mxcsr() {
    #[allow(deprecated)]
    let before = unsafe { std::arch::x86_64::_mm_getcsr() };
    let mut stream = ZwtvStream::new(FieldType::Free);
    let mut out = vec![StreamFrame::default(); 64];
    stream.push(&vec![0.001; 4800], &mut out);
    #[allow(deprecated)]
    let after_push = unsafe { std::arch::x86_64::_mm_getcsr() };
    assert_eq!(after_push & !0x3f, before & !0x3f);
    stream.flush(&mut out);
    #[allow(deprecated)]
    let after_flush = unsafe { std::arch::x86_64::_mm_getcsr() };
    assert_eq!(after_flush & !0x3f, before & !0x3f);
}

#[test]
#[ignore]
fn silence_throughput_within_20pct_of_sine() {
    let sine: Vec<f64> = (0..48_000 * 60)
        .map(|i| (2.0 * std::f64::consts::PI * 1000.0 * i as f64 / 48_000.0).sin() * 0.02)
        .collect();
    let silence = vec![0.0; sine.len()];
    let time = |signal: &[f64]| {
        let mut stream = ZwtvStream::new(FieldType::Free);
        let mut out = vec![StreamFrame::default(); 64];
        let start = std::time::Instant::now();
        for chunk in signal.chunks(480) {
            stream.push(chunk, &mut out);
        }
        start.elapsed()
    };
    let sine_time = time(&sine);
    let silence_time = time(&silence);
    eprintln!("sine {sine_time:?} silence {silence_time:?}");
    assert!(silence_time.as_secs_f64() < sine_time.as_secs_f64() * 1.2);
}
