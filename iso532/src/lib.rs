pub mod dsp;
pub mod error;
pub mod tables;
pub mod tables_noct;

pub use error::Iso532Error;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FieldType {
    Free,
    Diffuse,
}