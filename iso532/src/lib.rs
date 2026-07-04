pub mod core;
pub mod dsp;
pub mod error;
pub mod simd;
pub mod tables;
pub mod tables_noct;
pub mod zwst;
pub mod zwtv;

pub use error::Iso532Error;
pub use zwst::loudness_zwst;
pub use zwtv::loudness_zwtv;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FieldType {
    Free,
    Diffuse,
}

#[derive(Debug, Clone)]
pub struct LoudnessStationary {
    /// Total loudness [sone].
    pub n: f64,
    /// Specific loudness at 240 Bark steps [sone/Bark].
    pub n_specific: Vec<f64>,
    /// Bark axis from 0.1 to 24 Bark, 240 points.
    pub bark_axis: Vec<f64>,
}

#[derive(Debug, Clone)]
pub struct LoudnessTimeVarying {
    /// Total loudness over time [sone] on the returned time axis.
    pub n: Vec<f64>,
    /// Specific loudness, row-major (240 Bark steps, frames) [sone/Bark].
    pub n_specific: Vec<f64>,
    /// Bark axis from 0.1 to 24 Bark, 240 points.
    pub bark_axis: Vec<f64>,
    /// Time axis [s] on the ISO 532-1 2 ms output grid.
    pub time_axis: Vec<f64>,
}
