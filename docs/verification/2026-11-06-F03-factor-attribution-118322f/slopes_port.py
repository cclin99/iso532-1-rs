"""Factor-toggle port of the ISO 532-1 Annex A slope stage (f_calc_slopes, official C
ISO_532-1.c lines 839-937) and of the temporal weighting (f_temporal_weight_loudness /
f_lowpass_intp, as implemented in iso532 0.4.0 temporal_weighting.rs), in binary64.

Factors:
  usl_12_4 : value of USL[12][4] (0.24 shipped by MoSQITo / SQAT / iso532, 0.22 official C)
  eps      : band-edge constant added to every ZUP (C line 862 `_ZUP += .0001f`, SQAT line 528;
             0 in MoSQITo and iso532)
  f32      : if True, every table literal and inline constant of the slope stage is rounded to
             binary32 first (C declares the tables as `double` but writes `0.9f`, `0.1f`, `.0001f`)

The port is validated (validate.py) against iso532 0.4.0 (eps = 0, f32 = False must reproduce the
library bit for bit from its own nonlinear-decay output) and against SQAT v2.0 (eps = 1e-4).
"""
import numpy as np

ZUP = [0.9, 1.8, 2.8, 3.5, 4.4, 5.4, 6.6, 7.9, 9.2, 10.6, 12.3, 13.8, 15.2, 16.7, 18.1, 19.3, 20.6,
       21.8, 22.7, 23.6, 24.0]
RNS = [21.5, 18.0, 15.1, 11.5, 9.0, 6.1, 4.4, 3.1, 2.13, 1.36, 0.82, 0.42, 0.30, 0.22, 0.15, 0.10,
       0.035, 0.0]
USL = [[13.0, 8.2, 6.3, 5.5, 5.5, 5.5, 5.5, 5.5],
       [9.0, 7.5, 6.0, 5.1, 4.5, 4.5, 4.5, 4.5],
       [7.8, 6.7, 5.6, 4.9, 4.4, 3.9, 3.9, 3.9],
       [6.2, 5.4, 4.6, 4.0, 3.5, 3.2, 3.2, 3.2],
       [4.5, 3.8, 3.6, 3.2, 2.9, 2.7, 2.7, 2.7],
       [3.7, 3.0, 2.8, 2.35, 2.2, 2.2, 2.2, 2.2],
       [2.9, 2.3, 2.1, 1.9, 1.8, 1.7, 1.7, 1.7],
       [2.4, 1.7, 1.5, 1.35, 1.3, 1.3, 1.3, 1.3],
       [1.95, 1.45, 1.3, 1.15, 1.1, 1.1, 1.1, 1.1],
       [1.5, 1.2, 0.94, 0.86, 0.82, 0.82, 0.82, 0.82],
       [0.72, 0.67, 0.64, 0.63, 0.62, 0.62, 0.62, 0.62],
       [0.59, 0.53, 0.51, 0.50, 0.42, 0.42, 0.42, 0.42],
       [0.40, 0.33, 0.26, 0.24, 0.24, 0.22, 0.22, 0.22],
       [0.27, 0.21, 0.20, 0.18, 0.17, 0.17, 0.17, 0.17],
       [0.16, 0.15, 0.14, 0.12, 0.11, 0.11, 0.11, 0.11],
       [0.12, 0.11, 0.10, 0.08, 0.08, 0.08, 0.08, 0.08],
       [0.09, 0.08, 0.07, 0.06, 0.06, 0.06, 0.06, 0.05],
       [0.06, 0.05, 0.03, 0.02, 0.02, 0.02, 0.02, 0.02]]


def f32(x):
    return float(np.float32(x))


class Slopes:
    def __init__(self, usl_12_4=0.24, eps=0.0, f32_literals=False):
        r = f32 if f32_literals else (lambda v: float(v))
        self.zup = [r(z) + r(eps) for z in ZUP]
        self.rns = [r(v) for v in RNS]
        usl = [row[:] for row in USL]
        usl[12][4] = usl_12_4
        self.usl = [[r(v) for v in row] for row in usl]
        self.step = r(0.1)
        self.usl_12_4, self.eps, self.f32 = usl_12_4, eps, f32_literals

    def frame(self, core, want_spec=False):
        """One frame: core = 21 core-loudness values -> (N, spec[240] or None). Literal port of the
        C do/while structure; IdxNS is capped at 240 as the C arrays are sized N_BARK_BANDS."""
        zup, rns, usl, step = self.zup, self.rns, self.usl, self.step
        n1 = 0.0
        z = step
        z1 = 0.0
        idx_rns = 0
        idx_ns = 0
        total = 0.0
        spec = [0.0] * 240 if want_spec else None
        for i in range(21):
            corel = core[i]
            _zup = zup[i]
            cbn = min(max(i - 1, 0), 7)  # C: IdxCBN = IdxCL - 1, clamped to N_CB_RANGES-1 (negative index for band 0 never read: N1 = 0 there)
            if i == 0:
                cbn = -1
            while True:
                if n1 > corel:
                    _usl = usl[idx_rns][cbn]
                    n2 = rns[idx_rns]
                    if n2 < corel:
                        n2 = corel
                    dz = (n1 - n2) / _usl
                    z2 = z1 + dz
                    next_band = False
                    if z2 > _zup:
                        next_band = True
                        z2 = _zup
                        dz = z2 - z1
                        n2 = n1 - dz * _usl
                    total += dz * (n1 + n2) / 2.0
                    zk = z
                    while zk <= z2:
                        if idx_ns < 240:
                            if spec is not None:
                                spec[idx_ns] = n1 - (zk - z1) * _usl
                            idx_ns += 1
                        zk = zk + step
                    z = zk
                else:
                    if n1 < corel:
                        idx_rns = 0
                        while idx_rns < 18 and rns[idx_rns] >= corel:
                            idx_rns += 1
                    next_band = True
                    z2 = _zup
                    n2 = corel
                    total += n2 * (z2 - z1)
                    zk = z
                    while zk <= z2:
                        if idx_ns < 240:
                            if spec is not None:
                                spec[idx_ns] = n2
                            idx_ns += 1
                        zk = zk + step
                    z = zk
                while n2 <= rns[idx_rns] and idx_rns < 17:
                    idx_rns += 1
                if idx_rns > 17:
                    idx_rns = 17
                z1 = z2
                n1 = n2
                if next_band:
                    break
            if total < 0.0:
                total = 0.0
        return total, spec, idx_ns


def temporal_weighting(loud):
    """iso532 0.4.0 TwState (= C f_lowpass_intp with 24 interpolated sub-steps at 48 kHz)."""
    lp_iter = 24
    fs = 2000.0

    def coeff(tau):
        a1 = np.exp(-1.0 / (fs * lp_iter * tau))
        return 1.0 - a1, a1

    bf, bs = coeff(3.5e-3), coeff(70e-3)
    yf = ys = 0.0
    prev = 0.0
    has_prev = False
    out = np.empty(len(loud))
    for t, l in enumerate(loud):
        if has_prev:
            delta = (l - prev) / lp_iter
            for k in range(1, lp_iter):
                ui = prev + delta * k
                yf = bf[0] * ui + bf[1] * yf
                ys = bs[0] * ui + bs[1] * ys
        yf = bf[0] * l + bf[1] * yf
        ys = bs[0] * l + bs[1] * ys
        prev = l
        has_prev = True
        out[t] = 0.47 * yf + 0.53 * ys
    return out


def tv_pipeline(nl, slopes, want_spec=False, out_decim=4):
    """nl: (21, n_time) nonlinear-decay output at 2 kHz -> N(t) on the 2 ms output grid (every 4th
    frame after temporal weighting, as iso532 0.4.0 / the official CLI) and optionally the specific
    loudness (240, n_out) at the output frames."""
    n_time = nl.shape[1]
    loud = np.empty(n_time)
    n_out = -(-n_time // out_decim)
    spec = np.empty((240, n_out)) if want_spec else None
    for t in range(n_time):
        ws = want_spec and t % out_decim == 0
        total, sp, _ = slopes.frame(nl[:, t], ws)
        loud[t] = total
        if ws:
            spec[:, t // out_decim] = sp
    filt = temporal_weighting(loud)
    return filt[::out_decim], spec, loud
