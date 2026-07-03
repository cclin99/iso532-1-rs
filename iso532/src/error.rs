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
