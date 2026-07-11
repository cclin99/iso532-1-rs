use thiserror::Error;

#[derive(Debug, Error, PartialEq)]
pub enum Iso532Error {
    #[error("1/3 octave band level exceeds 120 dB below 300 Hz; Zwicker method not applicable")]
    LevelExceeds120dB,
    #[error("signal too short: got {got} samples, need at least {need}")]
    SignalTooShort { got: usize, need: usize },
    #[error("sampling rate must be 48000 Hz, got {0}")]
    UnsupportedSampleRate(f64),
}

impl Iso532Error {
    /// 穩定數值代碼；C ABI 的正值錯誤碼鏡像本表。
    pub fn code(&self) -> i32 {
        match self {
            Self::LevelExceeds120dB => 1,
            Self::SignalTooShort { .. } => 2,
            Self::UnsupportedSampleRate(_) => 3,
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
    }
}
