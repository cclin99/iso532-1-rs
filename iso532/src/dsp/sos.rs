#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Sos {
    /// numerator [b0, b1, b2]
    pub b: [f64; 3],
    /// denominator [a1, a2] (a0 normalized to 1)
    pub a: [f64; 2],
}

/// Cascade of biquads, direct form II transposed, in place.
pub fn sosfilt(sections: &[Sos], x: &mut [f64]) {
    for s in sections {
        let (mut z0, mut z1) = (0.0f64, 0.0f64);
        for v in x.iter_mut() {
            let xin = *v;
            let y = s.b[0] * xin + z0;
            z0 = s.b[1] * xin - s.a[0] * y + z1;
            z1 = s.b[2] * xin - s.a[1] * y;
            *v = y;
        }
    }
}

/// Like sosfilt but with initial state `zi` (per section [z0, z1]),
/// returning the final state. Needed by sosfiltfilt.
pub fn sosfilt_zi_run(sections: &[Sos], x: &mut [f64], zi: &mut [[f64; 2]]) {
    for (s, z) in sections.iter().zip(zi.iter_mut()) {
        let (mut z0, mut z1) = (z[0], z[1]);
        for v in x.iter_mut() {
            let xin = *v;
            let y = s.b[0] * xin + z0;
            z0 = s.b[1] * xin - s.a[0] * y + z1;
            z1 = s.b[2] * xin - s.a[1] * y;
            *v = y;
        }
        *z = [z0, z1];
    }
}

/// scipy sosfilt_zi: steady state per section for unit step input,
/// scaled through the cascade by the cumulative DC gain.
pub fn sosfilt_zi(sections: &[Sos]) -> Vec<[f64; 2]> {
    let mut scale = 1.0;
    sections
        .iter()
        .map(|s| {
            let g = (s.b[0] + s.b[1] + s.b[2]) / (1.0 + s.a[0] + s.a[1]);
            let zi = [scale * (g - s.b[0]), scale * (s.b[2] - s.a[1] * g)];
            scale *= g;
            zi
        })
        .collect()
}

/// First-order lowpass `y[n] = b0*x[n] + a1*y[n-1]`, in place.
pub fn onepole(b0: f64, a1: f64, x: &mut [f64]) {
    let mut y = 0.0f64;
    for v in x.iter_mut() {
        y = b0 * *v + a1 * y;
        *v = y;
    }
}
