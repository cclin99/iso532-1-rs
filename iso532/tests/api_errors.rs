use iso532::{loudness_zwst, loudness_zwtv, FieldType, Iso532Error};

#[test]
fn loudness_zwst_rejects_unsupported_sample_rate() {
    let x = vec![0.0; 4800];
    assert_eq!(
        loudness_zwst(&x, 44_100.0, FieldType::Free).unwrap_err(),
        Iso532Error::UnsupportedSampleRate(44_100.0)
    );
}

#[test]
fn loudness_zwst_rejects_short_signal() {
    let x = vec![0.0; 4799];
    assert_eq!(
        loudness_zwst(&x, 48_000.0, FieldType::Free).unwrap_err(),
        Iso532Error::SignalTooShort {
            got: 4799,
            need: 4800
        }
    );
}

#[test]
fn loudness_zwtv_rejects_unsupported_sample_rate() {
    let x = vec![0.0; 4800];
    assert_eq!(
        loudness_zwtv(&x, 44_100.0, FieldType::Free).unwrap_err(),
        Iso532Error::UnsupportedSampleRate(44_100.0)
    );
}

#[test]
fn loudness_zwtv_rejects_short_signal() {
    let x = vec![0.0; 4799];
    assert_eq!(
        loudness_zwtv(&x, 48_000.0, FieldType::Free).unwrap_err(),
        Iso532Error::SignalTooShort {
            got: 4799,
            need: 4800
        }
    );
}

// ---- C-02: batch functions reject non-finite input (error code 4) ----------

fn finite_signal() -> Vec<f64> {
    (0..48_000)
        .map(|i| 0.02 * (2.0 * std::f64::consts::PI * 1000.0 * i as f64 / 48_000.0).sin())
        .collect()
}

#[test]
fn nonfinite_error_code_is_frozen_at_4() {
    assert_eq!(Iso532Error::NonFiniteInput { idx: 0 }.code(), 4);
}

#[test]
fn batch_rejects_nan_and_infinities_at_head_middle_and_tail() {
    for (label, value) in [
        ("nan", f64::NAN),
        ("+inf", f64::INFINITY),
        ("-inf", f64::NEG_INFINITY),
    ] {
        for idx in [0usize, 24_000, 47_999] {
            let mut x = finite_signal();
            x[idx] = value;
            assert_eq!(
                loudness_zwst(&x, 48_000.0, FieldType::Free).unwrap_err(),
                Iso532Error::NonFiniteInput { idx },
                "zwst {label} at {idx}"
            );
            assert_eq!(
                loudness_zwtv(&x, 48_000.0, FieldType::Free).unwrap_err(),
                Iso532Error::NonFiniteInput { idx },
                "zwtv {label} at {idx}"
            );
        }
    }
}

#[test]
fn batch_reports_the_first_offending_sample() {
    let mut x = finite_signal();
    x[100] = f64::NAN;
    x[50] = f64::INFINITY;
    assert_eq!(
        loudness_zwtv(&x, 48_000.0, FieldType::Free).unwrap_err(),
        Iso532Error::NonFiniteInput { idx: 50 }
    );
}

#[test]
fn sample_rate_and_length_errors_take_precedence_over_finiteness() {
    let mut x = finite_signal();
    x[0] = f64::NAN;
    assert_eq!(
        loudness_zwtv(&x, 44_100.0, FieldType::Free).unwrap_err(),
        Iso532Error::UnsupportedSampleRate(44_100.0)
    );
    let short = vec![f64::NAN; 4799];
    assert_eq!(
        loudness_zwst(&short, 48_000.0, FieldType::Free).unwrap_err(),
        Iso532Error::SignalTooShort {
            got: 4799,
            need: 4800
        }
    );
}

#[test]
fn subnormal_zero_and_large_finite_samples_are_not_rejected_as_nonfinite() {
    // Subnormals and exact zeros are valid, quiet input.
    let mut x = finite_signal();
    x[10] = f64::MIN_POSITIVE / 8.0;
    x[11] = 0.0;
    x[12] = -0.0;
    assert!(loudness_zwst(&x, 48_000.0, FieldType::Free).is_ok());
    assert!(loudness_zwtv(&x, 48_000.0, FieldType::Free).is_ok());
    // A huge finite sample is finite input: whatever the outcome, it is not a
    // NonFiniteInput error and it does not panic.
    let mut loud = finite_signal();
    loud[24_000] = 1e300;
    for r in [
        loudness_zwst(&loud, 48_000.0, FieldType::Free).map(|_| ()),
        loudness_zwtv(&loud, 48_000.0, FieldType::Free).map(|_| ()),
    ] {
        if let Err(e) = r {
            assert!(!matches!(e, Iso532Error::NonFiniteInput { .. }), "{e}");
        }
    }
}

#[test]
fn stream_still_flags_instead_of_failing() {
    use iso532::{FrameFlags, StreamFrame, ZwtvStream};
    let mut x = finite_signal();
    x[4800] = f64::NAN;
    let mut stream = ZwtvStream::new(FieldType::Free);
    let mut out = vec![StreamFrame::default(); ZwtvStream::max_frames_for_chunk(x.len())];
    let n = stream.push(&x, &mut out);
    let n = n + stream.flush(&mut out[n..]);
    assert!(n > 0);
    assert!(out[..n]
        .iter()
        .any(|f| f.flags.contains(FrameFlags::NONFINITE_INPUT)));
    assert!(out[..n].iter().all(|f| f.n.is_finite()));
}
