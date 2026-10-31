//! Fail-closed verdict for ISO 532-1 Annex B comparisons (V-01).
//!
//! Tolerance: `|got - reference| <= max(0.1, 0.05 * |reference|)`, the rule the
//! official Annex B workbook applies per point (`docs/修正報告2.md` §11.5). This
//! is the max rule, not the additive `0.1 + 0.05 * |reference|`; for non-negative
//! operands `max(a, b) <= a + b`, so the max rule is never looser.
//!
//! Invalid data never folds into `Pass`: empty curves, length mismatch, any
//! non-finite value on either side, and any negative reference value produce
//! `Verdict::Invalid` without comparing numbers. `Pass` requires zero exceptions;
//! the 1 % exception clause of Annex B is intentionally not implemented (D2).

// Shared by several test binaries; each one uses a different subset.
#![allow(dead_code)]

use std::path::{Path, PathBuf};

#[derive(Debug, Clone, PartialEq)]
pub enum InvalidReason {
    /// `got` or `reference` has no points.
    Empty,
    /// The two curves do not have the same number of points. No common-range
    /// comparison is attempted.
    LengthMismatch { got: usize, want: usize },
    /// A NaN or infinite value; `which` is `"got"` or `"reference"`.
    NonFinite { which: &'static str, idx: usize },
    /// Annex B loudness and specific loudness references are non-negative; a
    /// negative value means the wrong column or the wrong file was read.
    NegativeReference { idx: usize },
}

#[derive(Debug, Clone, PartialEq)]
pub enum Verdict {
    Pass {
        points: usize,
    },
    /// `exceptions` points exceed their tolerance. `worst_idx` is the point with
    /// the largest excess `|diff| - tol`; `worst_diff` is `|diff|` there.
    Fail {
        exceptions: usize,
        points: usize,
        worst_idx: usize,
        worst_diff: f64,
    },
    Invalid(InvalidReason),
}

impl Verdict {
    #[allow(dead_code)]
    pub fn is_pass(&self) -> bool {
        matches!(self, Verdict::Pass { .. })
    }
}

/// Per-point Annex B tolerance for a (finite, non-negative) reference value.
pub fn annexb_tolerance(reference: f64) -> f64 {
    f64::max(0.1, 0.05 * reference.abs())
}

/// Compare `got` against `reference` under the Annex B max rule, fail-closed.
pub fn annexb_verdict(got: &[f64], reference: &[f64]) -> Verdict {
    if got.is_empty() || reference.is_empty() {
        return Verdict::Invalid(InvalidReason::Empty);
    }
    if got.len() != reference.len() {
        return Verdict::Invalid(InvalidReason::LengthMismatch {
            got: got.len(),
            want: reference.len(),
        });
    }
    if let Some(idx) = got.iter().position(|v| !v.is_finite()) {
        return Verdict::Invalid(InvalidReason::NonFinite { which: "got", idx });
    }
    if let Some(idx) = reference.iter().position(|v| !v.is_finite()) {
        return Verdict::Invalid(InvalidReason::NonFinite {
            which: "reference",
            idx,
        });
    }
    if let Some(idx) = reference.iter().position(|v| *v < 0.0) {
        return Verdict::Invalid(InvalidReason::NegativeReference { idx });
    }

    let mut exceptions = 0usize;
    let mut worst_idx = 0usize;
    let mut worst_excess = f64::NEG_INFINITY;
    let mut worst_diff = 0.0;
    for (idx, (g, r)) in got.iter().zip(reference).enumerate() {
        let diff = (g - r).abs();
        let tol = annexb_tolerance(*r);
        if diff > tol {
            exceptions += 1;
            let excess = diff - tol;
            if excess > worst_excess {
                worst_excess = excess;
                worst_idx = idx;
                worst_diff = diff;
            }
        }
    }
    if exceptions == 0 {
        Verdict::Pass { points: got.len() }
    } else {
        Verdict::Fail {
            exceptions,
            points: got.len(),
            worst_idx,
            worst_diff,
        }
    }
}

/// Directory holding the Annex B CSV references (`data/annexb`, gitignored).
#[allow(dead_code)]
pub fn annexb_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .join("data/annexb")
}

/// Strict reader for the Annex B specific-loudness CSV files: one header line,
/// then exactly one finite number per line. A UTF-8 BOM is accepted on the header
/// only. Any blank, unparsable, or BOM-carrying data line panics with the path
/// and 1-based line number; nothing is skipped silently. The caller still has to
/// check the row count it expects (240 Bark rows).
pub fn annexb_csv_path(path: &Path) -> Vec<f64> {
    let txt = std::fs::read_to_string(path)
        .unwrap_or_else(|e| panic!("missing {path:?} (run tools/setup_env.sh): {e}"));
    let mut out = Vec::new();
    for (line_idx, raw) in txt.lines().enumerate() {
        let line_no = line_idx + 1;
        if line_idx == 0 {
            // Header line: BOM allowed here and only here.
            continue;
        }
        assert!(
            !raw.contains('\u{feff}'),
            "{}:{line_no}: BOM outside the header line",
            path.display()
        );
        let text = raw.trim();
        assert!(
            !text.is_empty(),
            "{}:{line_no}: blank line is not a valid Annex B row",
            path.display()
        );
        let value: f64 = text
            .parse()
            .unwrap_or_else(|_| panic!("{}:{line_no}: cannot parse {text:?}", path.display()));
        out.push(value);
    }
    out
}

/// Name-based wrapper kept for the existing Annex B tests.
#[allow(dead_code)]
pub fn annexb_csv(file: &str) -> Vec<f64> {
    annexb_csv_path(&annexb_dir().join(file))
}
