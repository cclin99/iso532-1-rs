use iso532::{loudness_zwst, FieldType, Iso532Error};

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
