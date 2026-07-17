//! Sone to phon conversion.

/// Convert non-negative loudness in sone to loudness level in phon.
pub fn sone2phon(n: f64) -> f64 {
    if n >= 1.0 {
        40.0 + 10.0 * n.log2()
    } else {
        40.0 * (n + 0.0005).powf(0.35)
    }
}

#[cfg(test)]
mod tests {
    use super::sone2phon;

    #[test]
    fn anchors_and_monotonicity() {
        assert_eq!(sone2phon(1.0), 40.0);
        assert_eq!(sone2phon(2.0), 50.0);
        assert_eq!(sone2phon(4.0), 60.0);
        assert!((sone2phon(0.5) - 40.0 * 0.5005_f64.powf(0.35)).abs() < 1e-12);
        assert!((sone2phon(0.0) - 40.0 * 0.0005_f64.powf(0.35)).abs() < 1e-12);
        let mut prev = f64::NEG_INFINITY;
        for i in 0..=1000 {
            let p = sone2phon(i as f64 * 0.02);
            assert!(p >= prev, "non-monotonic at {i}");
            prev = p;
        }
    }
}
