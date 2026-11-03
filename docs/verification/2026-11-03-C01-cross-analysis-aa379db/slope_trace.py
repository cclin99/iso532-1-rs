"""Exact Python ports of the official Annex A `f_calc_slopes` (total only) and of the Rust
`calc_slopes_impl` (total only), validated bitwise against the stage arrays left in the
tail-root-cause scratch directory, plus a per-frame band-level tracer.

Environment: C01_WORK must point at the tail-root-cause scratch directory
(`<REPO>/tmp/c01-tail-root-cause-aa379db-run2`), which holds `signal-*/R-pipeline/*.bin` and
`signal-*/C-slope-on-Rnl-total.bin` produced by Astra's run_experiment.py.

Modes:
  validate <sig> [step]   port(C) vs C-slope-on-Rnl-total.bin, port(Rust) vs slope_raw.bin / slope_raw22.bin
  trace <sig> <frame>...  band with the largest contribution difference and its segment lists
  band0                   synthetic frames exercising the band-0 wrap-around of the Rust/MoSQITo algorithm
  band0scan               how often nm[20] > nm[0] > 0 occurs in the real NL histories (never: nm[20] == 0)
"""
import math
import os
import sys
import time

import numpy as np

ROOT = os.environ.get("C01_WORK")
if not ROOT:
    sys.exit("set C01_WORK to the tail-root-cause scratch directory")

ZUP = [0.9, 1.8, 2.8, 3.5, 4.4, 5.4, 6.6, 7.9, 9.2, 10.6, 12.3, 13.8, 15.2, 16.7, 18.1, 19.3, 20.6, 21.8, 22.7, 23.6, 24.0]
RNS = [21.5, 18.0, 15.1, 11.5, 9.0, 6.1, 4.4, 3.1, 2.13, 1.36, 0.82, 0.42, 0.30, 0.22, 0.15, 0.10, 0.035, 0.0]
USL = [[13.0, 8.2, 6.3, 5.5, 5.5, 5.5, 5.5, 5.5], [9.0, 7.5, 6.0, 5.1, 4.5, 4.5, 4.5, 4.5], [7.8, 6.7, 5.6, 4.9, 4.4, 3.9, 3.9, 3.9],
       [6.2, 5.4, 4.6, 4.0, 3.5, 3.2, 3.2, 3.2], [4.5, 3.8, 3.6, 3.2, 2.9, 2.7, 2.7, 2.7], [3.7, 3.0, 2.8, 2.35, 2.2, 2.2, 2.2, 2.2],
       [2.9, 2.3, 2.1, 1.9, 1.8, 1.7, 1.7, 1.7], [2.4, 1.7, 1.5, 1.35, 1.3, 1.3, 1.3, 1.3], [1.95, 1.45, 1.3, 1.15, 1.1, 1.1, 1.1, 1.1],
       [1.5, 1.2, 0.94, 0.86, 0.82, 0.82, 0.82, 0.82], [0.72, 0.67, 0.64, 0.63, 0.62, 0.62, 0.62, 0.62], [0.59, 0.53, 0.51, 0.50, 0.42, 0.42, 0.42, 0.42],
       [0.40, 0.33, 0.26, 0.24, 0.24, 0.22, 0.22, 0.22], [0.27, 0.21, 0.20, 0.18, 0.17, 0.17, 0.17, 0.17], [0.16, 0.15, 0.14, 0.12, 0.11, 0.11, 0.11, 0.11],
       [0.12, 0.11, 0.10, 0.08, 0.08, 0.08, 0.08, 0.08], [0.09, 0.08, 0.07, 0.06, 0.06, 0.06, 0.06, 0.05], [0.06, 0.05, 0.03, 0.02, 0.02, 0.02, 0.02, 0.02]]
USL22 = [r[:] for r in USL]
USL22[12][4] = 0.22
f32 = lambda v: float(np.float32(v))
# the official C stores every table constant as a float literal promoted to double
ZUPc = [f32(v) for v in ZUP]
RNSc = [f32(v) for v in RNS]
USLc = [[f32(v) for v in r] for r in USL22]
EPS = f32(0.0001)


def c_slopes(core, trace=None, eps=EPS):
    """Port of ISO_532-1.c f_calc_slopes (lines 839-937), total loudness only."""
    N1 = 0.0; Z1 = 0.0; IdxRNS = 0; L = 0.0; cum = []
    for i in range(21):
        CoreL = core[i]; _ZUP = ZUPc[i] + eps; IdxCBN = min(i - 1, 7); nxt = 0; segs = []
        while True:
            if N1 > CoreL:
                assert i > 0
                _USL = USLc[IdxRNS][IdxCBN]; N2 = RNSc[IdxRNS]
                if N2 < CoreL:
                    N2 = CoreL
                DZ = (N1 - N2) / _USL; Z2 = Z1 + DZ; clip = False
                if Z2 > _ZUP:
                    nxt = 1; Z2 = _ZUP; DZ = Z2 - Z1; N2 = N1 - DZ * _USL; clip = True
                L += DZ * (N1 + N2) / 2.
                segs.append(('slope', IdxRNS, _USL, N1, N2, Z1, Z2, clip))
            else:
                if N1 < CoreL:
                    IdxRNS = 0
                    while IdxRNS < 18 and RNSc[IdxRNS] >= CoreL:
                        IdxRNS += 1
                    if IdxRNS > 17:
                        IdxRNS = 17
                nxt = 1; Z2 = _ZUP; N2 = CoreL; L += N2 * (Z2 - Z1)
                segs.append(('flat', IdxRNS, None, N1, N2, Z1, Z2, True))
            while N2 <= RNSc[IdxRNS] and IdxRNS < 17:
                IdxRNS += 1
            if IdxRNS > 17:
                IdxRNS = 17
            Z1 = Z2; N1 = N2
            if nxt:
                break
        cum.append(L)
        if trace is not None:
            trace.append(segs)
    if L < 0:
        L = 0
    return L, cum


def r8(v):
    """Rust `(value * 1e8).round() / 1e8` (round half away from zero)."""
    y = v * 100000000.0; a = abs(y); r = math.floor(a)
    if a - r >= 0.5:
        r += 1
    return math.copysign(r, y) / 100000000.0


RNS8 = [r8(v) for v in RNS]


def rns_index(v, eq):
    v = r8(v); idx = 0
    for r in RNS8:
        if (v <= r if eq else v < r):
            idx += 1
    return min(idx, 17)


def rust_slopes(nm, usl_tab, trace=None):
    """Port of iso532/src/core/calc_slopes.rs calc_slopes_impl at aa379db, total only, WITHOUT the
    final rounding (lines 161-165), i.e. the `slopes_raw` diagnostic variant."""
    zup_ea = [int(z * 10.0) for z in ZUP]
    pz = lambda i: 0 if i == 0 else zup_ea[i - 1]
    uv = lambda idx, i: usl_tab[idx][min(i - 1 if i > 0 else 7, 7)]
    n2 = [1.0] * 240; z2 = [1.0] * 240; usl = [1.0] * 240; dz = [1.0] * 240; rv = [1.0] * 240
    ri = [rns_index(nm[i], False) for i in range(21)]
    for i in range(21):
        bdz = ZUP[1] if i < 2 else ZUP[i] - ZUP[i - 1]
        for j in range(pz(i), zup_ea[i]):
            n2[j] = nm[i]; dz[j] = bdz; z2[j] = ZUP[i]; usl[j] = usl_tab[ri[i]][min(i, 7)]; rv[j] = RNS[ri[i]]
    total = 0.0; n1 = 0.0; z1 = 0.0; cum = []
    for i in range(21):
        j0 = pz(i); before = 239 if j0 == 0 else j0 - 1; segs = []
        idx = rns_index(n2[before], False); rv[j0] = RNS[idx]; usl[j0] = uv(idx, i)
        mask = r8(n2[before]) > r8(nm[i])
        if not mask:
            total += n2[j0] * (z2[j0] - z1)
            segs.append(('flat', idx, None, n1, n2[j0], z1, z2[j0]))
            n1 = n2[j0]; z1 = z2[j0]
        if mask:
            mx = max(rv[before], nm[i]); z2[j0] = min((n1 - mx) / usl[j0] + z1, ZUP[i]); dz[j0] = z2[j0] - z1; n2[j0] = n1 - dz[j0] * usl[j0]
            total += dz[j0] * (n1 + n2[j0]) / 2.0
            segs.append(('slope', idx, usl[j0], n1, n2[j0], z1, z2[j0]))
            za = (ZUP[20] if i == 0 else ZUP[i - 1]) + 0.1; lastm = False; lastj = j0
            for j in range(j0, zup_ea[i]):
                lastj = j
                if j != j0:
                    z2[j] = z2[j - 1]; n2[j] = n2[j - 1]; dz[j] = dz[j - 1]; usl[j] = usl[j - 1]; rv[j] = rv[j - 1]
                mz = mask and r8(z2[j]) <= r8(za); lastm = mz
                if mz:
                    idx = rns_index(n2[j], True); rv[j] = RNS[idx]; usl[j] = uv(idx, i); n1 = n2[j]; z1 = z2[j]
                    m1 = r8(n1) <= r8(nm[i])
                    if m1:
                        n2[j] = nm[i]; z2[j] = ZUP[i]; dz[j] = z2[j] - z1; total += n2[j] * (z2[j] - z1)
                        segs.append(('flat', idx, None, n1, n2[j], z1, z2[j], 'grid', j))
                    else:
                        mx = max(rv[j], nm[i]); z2[j] = min((n1 - mx) / usl[j] + z1, ZUP[i]); dz[j] = z2[j] - z1; n2[j] = n1 - dz[j] * usl[j]
                        total += dz[j] * (n1 + n2[j]) / 2.0
                        segs.append(('slope', idx, usl[j], n1, n2[j], z1, z2[j], 'grid', j))
                    za += 0.1
                    if m1:
                        mask = False
                else:
                    za += 0.1
                z1 = z2[j]; n1 = n2[j]
                if not mask:
                    break
            z1 = z2[zup_ea[i] - 1]; n1 = n2[zup_ea[i] - 1]
            if lastm:
                idx = rns_index(n2[lastj], True); rv[lastj] = RNS[idx]; usl[lastj] = uv(idx, i)
        cum.append(total)
        if trace is not None:
            trace.append(segs)
    if total < 0:
        total = 0
    return total, cum


def rd(p):
    return np.fromfile(p, dtype='<f8')


def validate(sig, frames=None):
    d = f"{ROOT}/signal-{sig}"; nl = rd(f"{d}/R-pipeline/nl.bin"); n = len(nl) // 21; nl = nl.reshape(21, n)
    cs = rd(f"{d}/C-slope-on-Rnl-total.bin"); raw = rd(f"{d}/R-pipeline/slope_raw.bin"); raw22 = rd(f"{d}/R-pipeline/slope_raw22.bin")
    fr = range(n) if frames is None else frames
    bc = br = br22 = 0; mc = mr = mr22 = 0.0; t = time.time()
    for k in fr:
        core = list(nl[:, k]); c, _ = c_slopes(core); r, _ = rust_slopes(core, USL); r22, _ = rust_slopes(core, USL22)
        bc += (c != cs[k]); br += (r != raw[k]); br22 += (r22 != raw22[k])
        mc = max(mc, abs(c - cs[k])); mr = max(mr, abs(r - raw[k])); mr22 = max(mr22, abs(r22 - raw22[k]))
    print(f"[validate sig {sig}] frames={len(fr)} C-port bitwise mismatches={bc} (max {mc:.2e}); Rust24-port mismatches={br} (max {mr:.2e}); Rust22-port mismatches={br22} (max {mr22:.2e}); {time.time()-t:.0f}s")


def fmt(s):
    base = f"{s[0]:5s} rns={s[1]:2d} usl={s[2]} N1={s[3]:.6g} N2={s[4]:.6g} Z1={s[5]:.6g} Z2={s[6]:.6g}"
    return base + (" " + " ".join(str(x) for x in s[7:]) if len(s) > 7 else "")


def trace_frame(sig, nl, k):
    core = list(nl[:, k]); tc = []; tr = []
    c, cc = c_slopes(core, tc); r, cr = rust_slopes(core, USL22, tr)
    per = [(cr[i] - (cr[i - 1] if i else 0)) - (cc[i] - (cc[i - 1] if i else 0)) for i in range(21)]
    first = max(range(21), key=lambda i: abs(per[i]))
    print(f"\n--- sig {sig} frame {k}: C={c:.10f} Rust22={r:.10f} diff={r-c:+.3e}; band with largest |contribution diff|: {first} ({per[first]:+.3e}); per-band diffs>1e-6: {[(i, f'{per[i]:+.1e}') for i in range(21) if abs(per[i]) > 1e-6]}")
    print("    nm:", ["%.4g" % v for v in core])
    for i in range(max(first - 1, 0), min(first + 2, 21)):
        pc = cc[i] - (cc[i - 1] if i else 0); pr = cr[i] - (cr[i - 1] if i else 0)
        print(f"    band {i} nm={core[i]:.6g} ZUP={ZUP[i]}  contribution C={pc:.6e} R={pr:.6e} (R-C={pr-pc:+.3e})")
        for s in tc[i]:
            print("       C ", fmt(s))
        for s in tr[i]:
            print("       R ", fmt(s))


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "validate":
        sig = int(sys.argv[2]); step = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        d = f"{ROOT}/signal-{sig}"; n = len(rd(f"{d}/C-slope-on-Rnl-total.bin"))
        validate(sig, range(0, n, step))
    if mode == "trace":
        sig = int(sys.argv[2]); frames = [int(x) for x in sys.argv[3:]]
        d = f"{ROOT}/signal-{sig}"; nl = rd(f"{d}/R-pipeline/nl.bin"); n = len(nl) // 21; nl = nl.reshape(21, n)
        for k in frames:
            trace_frame(sig, nl, k)
    if mode == "band0":
        for nm0, nm20 in [(0.5, 1.0), (0.5, 0.3), (0.0, 1.0), (0.2, 2.0), (1.0, 1.0)]:
            core = [0.0] * 21; core[0] = nm0; core[20] = nm20
            c, _ = c_slopes(core); r, _ = rust_slopes(core, USL22)
            print(f"band0 test nm0={nm0} nm20={nm20}: C={c:.9f} Rust={r:.9f} diff={r-c:+.3e}")
        core = [0.3] * 21; core[0] = 0.5; core[20] = 1.0
        c, _ = c_slopes(core); r, _ = rust_slopes(core, USL22)
        print(f"band0 test all0.3 nm0=0.5 nm20=1.0: C={c:.9f} Rust={r:.9f} diff={r-c:+.3e}")
    if mode == "band0scan":
        for sig in (18, 23, 24, 25):
            d = f"{ROOT}/signal-{sig}"; nl = rd(f"{d}/R-pipeline/nl.bin"); n = len(nl) // 21; nl = nl.reshape(21, n)
            hit = (nl[20] > nl[0]) & (nl[0] > 0)
            print(f"sig {sig}: frames with nm20>nm0>0: {hit.sum()}/{n}; frames nm0>0: {(nl[0]>0).sum()}; frames nm20>0: {(nl[20]>0).sum()}")
