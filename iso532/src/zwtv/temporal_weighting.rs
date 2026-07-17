const LP_ITER: usize = 24;
const SAMPLE_RATE: f64 = 2000.0;

fn lp_coeff(tau: f64) -> (f64, f64) {
    let a1 = (-1.0 / (SAMPLE_RATE * LP_ITER as f64 * tau)).exp();
    (1.0 - a1, a1)
}

pub(crate) struct TwState {
    y_fast: f64,
    y_slow: f64,
    bf: (f64, f64),
    bs: (f64, f64),
    prev: f64,
    has_prev: bool,
}

impl TwState {
    pub(crate) fn new() -> Self {
        Self {
            y_fast: 0.0,
            y_slow: 0.0,
            bf: lp_coeff(3.5e-3),
            bs: lp_coeff(70e-3),
            prev: 0.0,
            has_prev: false,
        }
    }

    #[inline]
    pub(crate) fn advance(&mut self, loud_t: f64) -> f64 {
        if self.has_prev {
            let delta = (loud_t - self.prev) / LP_ITER as f64;
            for k in 1..LP_ITER {
                let ui = self.prev + delta * k as f64;
                self.y_fast = self.bf.0 * ui + self.bf.1 * self.y_fast;
                self.y_slow = self.bs.0 * ui + self.bs.1 * self.y_slow;
            }
        }
        self.y_fast = self.bf.0 * loud_t + self.bf.1 * self.y_fast;
        self.y_slow = self.bs.0 * loud_t + self.bs.1 * self.y_slow;
        self.prev = loud_t;
        self.has_prev = true;
        0.47 * self.y_fast + 0.53 * self.y_slow
    }
}

/// Duration-dependent loudness perception: 0.47*LP(3.5ms) + 0.53*LP(70ms).
pub fn temporal_weighting(loudness: &[f64]) -> Vec<f64> {
    let mut state = TwState::new();
    loudness.iter().map(|&l| state.advance(l)).collect()
}
