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
    fn anchors_and_branch_monotonicity() {
        assert_eq!(sone2phon(1.0), 40.0);
        assert_eq!(sone2phon(2.0), 50.0);
        assert_eq!(sone2phon(4.0), 60.0);
        assert!((sone2phon(0.5) - 40.0 * 0.5005_f64.powf(0.35)).abs() < 1e-12);
        assert!((sone2phon(0.0) - 40.0 * 0.0005_f64.powf(0.35)).abs() < 1e-12);
        for (start, step, count) in [(0.0, 0.00001, 99_999), (1.0, 0.0001, 190_000)] {
            let mut prev = sone2phon(start);
            for i in 1..=count {
                let p = sone2phon(start + i as f64 * step);
                assert!(p >= prev, "non-monotonic within branch at {i}");
                prev = p;
            }
        }
        // The inherited ISO/mosqito formula restarts at exactly 40 phon.
        assert!(sone2phon(1.0 - 1e-9) > sone2phon(1.0));
    }
}
