use super::sos::{sosfilt_zi, sosfilt_zi_run, Sos};
use crate::tables_noct::{CHEBY_QS, CHEBY_SOS};

/// Odd extension padding as scipy.signal._arraytools.odd_ext.
fn odd_ext(x: &[f64], n: usize) -> Vec<f64> {
    assert!(x.len() > n, "padlen {n} >= signal length {}", x.len());
    let mut out = Vec::with_capacity(x.len() + 2 * n);
    let x0 = x[0];
    for i in (1..=n).rev() {
        out.push(2.0 * x0 - x[i]);
    }
    out.extend_from_slice(x);
    let xl = x[x.len() - 1];
    for i in 2..=(n + 1) {
        out.push(2.0 * xl - x[x.len() - i]);
    }
    out
}

/// scipy.signal.sosfiltfilt with defaults (padtype='odd', padlen=None).
pub fn sosfiltfilt(sections: &[Sos], x: &[f64]) -> Vec<f64> {
    let nb2 = sections.iter().filter(|s| s.b[2] == 0.0).count();
    let na2 = sections.iter().filter(|s| s.a[1] == 0.0).count();
    let padlen = 3 * (2 * sections.len() + 1 - nb2.min(na2));
    let zi_unit = sosfilt_zi(sections);

    let mut ext = odd_ext(x, padlen);
    let x0 = ext[0];
    let mut zi: Vec<[f64; 2]> = zi_unit.iter().map(|z| [z[0] * x0, z[1] * x0]).collect();
    sosfilt_zi_run(sections, &mut ext, &mut zi);

    ext.reverse();
    let y0 = ext[0];
    let mut zi: Vec<[f64; 2]> = zi_unit.iter().map(|z| [z[0] * y0, z[1] * y0]).collect();
    sosfilt_zi_run(sections, &mut ext, &mut zi);
    ext.reverse();
    ext[padlen..ext.len() - padlen].to_vec()
}

/// scipy.signal.decimate(x, q) with defaults: Chebyshev-I order 8, zero-phase.
pub fn decimate(x: &[f64], q: usize) -> Vec<f64> {
    let idx = CHEBY_QS
        .iter()
        .position(|&c| c == q)
        .unwrap_or_else(|| panic!("no baked Chebyshev SOS for q={q}"));
    let y = sosfiltfilt(&CHEBY_SOS[idx], x);
    y.iter().step_by(q).copied().collect()
}
