#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Sos {
    /// numerator [b0, b1, b2]
    pub b: [f64; 3],
    /// denominator [a1, a2] (a0 normalized to 1)
    pub a: [f64; 2],
}
