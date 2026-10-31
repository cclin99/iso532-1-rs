use thiserror::Error;

#[derive(Debug, Error, PartialEq)]
pub enum Iso532Error {
    #[error("1/3 octave band level exceeds 120 dB below 300 Hz; Zwicker method not applicable")]
    LevelExceeds120dB,
    #[error("signal too short: got {got} samples, need at least {need}")]
    SignalTooShort { got: usize, need: usize },
    #[error("sampling rate must be 48000 Hz, got {0}")]
    UnsupportedSampleRate(f64),
    /// A NaN or infinite sample in a batch input (`loudness_zwst`,
    /// `loudness_zwtv`, `ZwtvProcessor`). Batch functions have the whole
    /// signal and reject it; the stream path instead zeroes the sample and
    /// raises `FrameFlags::NONFINITE_INPUT` because it must never fail on the
    /// audio thread. `idx` is the first offending sample.
    #[error("non-finite sample (NaN or infinite) at index {idx}; batch input is rejected")]
    NonFiniteInput { idx: usize },
}

impl Iso532Error {
    /// 穩定數值代碼；C ABI 的正值錯誤碼鏡像本表。
    pub fn code(&self) -> i32 {
        match self {
            Self::LevelExceeds120dB => 1,
            Self::SignalTooShort { .. } => 2,
            Self::UnsupportedSampleRate(_) => 3,
            Self::NonFiniteInput { .. } => 4,
        }
    }

    /// Batch-input finiteness check shared by the stationary and time-varying
    /// entry points. Runs after the sample-rate and length checks.
    pub(crate) fn check_finite(signal: &[f64]) -> Result<(), Self> {
        match signal.iter().position(|v| !v.is_finite()) {
            Some(idx) => Err(Self::NonFiniteInput { idx }),
            None => Ok(()),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::Iso532Error;

    #[test]
    fn error_codes_are_frozen() {
        assert_eq!(Iso532Error::LevelExceeds120dB.code(), 1);
        assert_eq!(Iso532Error::SignalTooShort { got: 0, need: 4800 }.code(), 2);
        assert_eq!(Iso532Error::UnsupportedSampleRate(44_100.0).code(), 3);
        assert_eq!(Iso532Error::NonFiniteInput { idx: 7 }.code(), 4);
    }

    #[test]
    fn check_finite_reports_first_offending_index() {
        assert_eq!(Iso532Error::check_finite(&[0.0, 1.0, -1.0]), Ok(()));
        assert_eq!(
            Iso532Error::check_finite(&[0.0, f64::NAN, f64::INFINITY]),
            Err(Iso532Error::NonFiniteInput { idx: 1 })
        );
        assert_eq!(
            Iso532Error::check_finite(&[f64::NEG_INFINITY]),
            Err(Iso532Error::NonFiniteInput { idx: 0 })
        );
        // Subnormals and the largest finite value are valid input.
        assert_eq!(
            Iso532Error::check_finite(&[f64::MIN_POSITIVE / 4.0, f64::MAX, -f64::MAX]),
            Ok(())
        );
    }
}
