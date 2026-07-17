//! ISO 532-1:2017 Zwicker loudness calculation.
//!
//! This crate implements stationary (`loudness_zwst`) and time-varying
//! (`loudness_zwtv`) loudness for calibrated 48 kHz pressure signals. The
//! implementation follows the ISO 532-1 / Annex B validation path used by the
//! repository golden data and uses AVX2+FMA dispatch for the time-varying
//! filter bank when the host CPU supports it.
//!
//! # Stationary example
//!
//! ```no_run
//! use iso532::{loudness_zwst, FieldType};
//!
//! # fn main() -> Result<(), iso532::Iso532Error> {
//! let signal = vec![0.0; 48_000];
//! let result = loudness_zwst(&signal, 48_000.0, FieldType::Free)?;
//! println!("N = {:.3} sone", result.n);
//! # Ok(())
//! # }
//! ```
//!
//! # Time-varying example
//!
//! ```no_run
//! use iso532::{loudness_zwtv, FieldType};
//!
//! # fn main() -> Result<(), iso532::Iso532Error> {
//! let signal = vec![0.0; 48_000];
//! let result = loudness_zwtv(&signal, 48_000.0, FieldType::Free)?;
//! println!("{} loudness samples", result.n.len());
//! # Ok(())
//! # }
//! ```
//!
//! # Limitations
//!
//! The public signal APIs currently accept only 48 kHz input. Signals shorter
//! than 0.1 s are rejected, and ISO 532-1 low-frequency applicability checks
//! are surfaced as `Iso532Error`.
pub mod core;
pub mod dsp;
pub mod error;
pub mod simd;
mod sone2phon;
pub mod tables;
pub mod tables_noct;
pub mod zwst;
pub mod zwtv;

pub use error::Iso532Error;
pub use sone2phon::sone2phon;
pub use zwst::loudness_zwst;
pub use zwtv::stream::{FrameFlags, StreamFrame, ZwtvStream, N_WARMUP_FRAMES};
pub use zwtv::{loudness_zwtv, zwtv_out_frames, ZwtvProcessor};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FieldType {
    Free,
    Diffuse,
}

impl TryFrom<i32> for FieldType {
    type Error = i32;

    fn try_from(value: i32) -> Result<Self, Self::Error> {
        match value {
            0 => Ok(Self::Free),
            1 => Ok(Self::Diffuse),
            other => Err(other),
        }
    }
}

impl std::str::FromStr for FieldType {
    type Err = ();

    fn from_str(value: &str) -> Result<Self, Self::Err> {
        match value {
            "free" => Ok(Self::Free),
            "diffuse" => Ok(Self::Diffuse),
            _ => Err(()),
        }
    }
}

#[cfg(test)]
mod field_type_tests {
    use crate::FieldType;

    #[test]
    fn try_from_i32_matches_abi_table() {
        assert_eq!(FieldType::try_from(0), Ok(FieldType::Free));
        assert_eq!(FieldType::try_from(1), Ok(FieldType::Diffuse));
        assert_eq!(FieldType::try_from(2), Err(2));
        assert_eq!(FieldType::try_from(-1), Err(-1));
    }

    #[test]
    fn from_str_matches_py_vocabulary() {
        assert_eq!("free".parse(), Ok(FieldType::Free));
        assert_eq!("diffuse".parse(), Ok(FieldType::Diffuse));
        assert!("FREE".parse::<FieldType>().is_err());
    }
}

#[derive(Debug, Clone)]
pub struct LoudnessStationary {
    /// Total loudness, in sone.
    pub n: f64,
    /// Specific loudness at 240 Bark steps [sone/Bark].
    pub n_specific: Vec<f64>,
    /// Bark axis from 0.1 to 24 Bark, 240 points.
    pub bark_axis: Vec<f64>,
}

#[derive(Debug, Clone)]
pub struct LoudnessTimeVarying {
    /// Total loudness over time, in sone, on the returned time axis.
    pub n: Vec<f64>,
    /// Specific loudness, row-major (240 Bark steps, frames) [sone/Bark].
    pub n_specific: Vec<f64>,
    /// Bark axis from 0.1 to 24 Bark, 240 points.
    pub bark_axis: Vec<f64>,
    /// Time axis, in seconds, on the ISO 532-1 2 ms output grid.
    pub time_axis: Vec<f64>,
}
