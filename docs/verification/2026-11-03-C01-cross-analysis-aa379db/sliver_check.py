"""F-05 hypothesis check: every 'sparse' frame (|Rust raw22 - C(eps=0, f64 tables)| > 1e-6) is a frame
where the Rust/MoSQITo grid loop ended with the slope branch still active before ZUP, so the flat
remainder of the band was never integrated. A port with that remainder restored the Annex A way
must match the C port to arithmetic noise, and the tail difference must close.
Requires C01_WORK (see slope_trace.py)."""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import slope_trace as st  # noqa: E402

ZUP, RNS = st.ZUP, st.RNS


def rust_slopes_fixed(nm, usl_tab):
    """st.rust_slopes plus: after each band's grid loop, if the slope branch is still active and the
    last segment ended before ZUP[i], complete the band as Annex A does (continue slope segments or
    flat-fill from (z1, n1) to ZUP[i])."""
    zup_ea = [int(z * 10.0) for z in ZUP]
    pz = lambda i: 0 if i == 0 else zup_ea[i - 1]
    uv = lambda idx, i: usl_tab[idx][min(i - 1 if i > 0 else 7, 7)]
    n2 = [1.0] * 240; z2 = [1.0] * 240; usl = [1.0] * 240; dz = [1.0] * 240; rv = [1.0] * 240
    ri = [st.rns_index(nm[i], False) for i in range(21)]
    for i in range(21):
        bdz = ZUP[1] if i < 2 else ZUP[i] - ZUP[i - 1]
        for j in range(pz(i), zup_ea[i]):
            n2[j] = nm[i]; dz[j] = bdz; z2[j] = ZUP[i]; usl[j] = usl_tab[ri[i]][min(i, 7)]; rv[j] = RNS[ri[i]]
    total = 0.0; n1 = 0.0; z1 = 0.0; fixes = 0
    for i in range(21):
        j0 = pz(i); before = 239 if j0 == 0 else j0 - 1
        idx = st.rns_index(n2[before], False); rv[j0] = RNS[idx]; usl[j0] = uv(idx, i)
        mask = st.r8(n2[before]) > st.r8(nm[i])
        if not mask:
            total += n2[j0] * (z2[j0] - z1); n1 = n2[j0]; z1 = z2[j0]
        if mask:
            mx = max(rv[before], nm[i]); z2[j0] = min((n1 - mx) / usl[j0] + z1, ZUP[i]); dz[j0] = z2[j0] - z1; n2[j0] = n1 - dz[j0] * usl[j0]
            total += dz[j0] * (n1 + n2[j0]) / 2.0
            za = (ZUP[20] if i == 0 else ZUP[i - 1]) + 0.1; lastm = False; lastj = j0
            for j in range(j0, zup_ea[i]):
                lastj = j
                if j != j0:
                    z2[j] = z2[j - 1]; n2[j] = n2[j - 1]; dz[j] = dz[j - 1]; usl[j] = usl[j - 1]; rv[j] = rv[j - 1]
                mz = mask and st.r8(z2[j]) <= st.r8(za); lastm = mz
                if mz:
                    idx = st.rns_index(n2[j], True); rv[j] = RNS[idx]; usl[j] = uv(idx, i); n1 = n2[j]; z1 = z2[j]
                    m1 = st.r8(n1) <= st.r8(nm[i])
                    if m1:
                        n2[j] = nm[i]; z2[j] = ZUP[i]; dz[j] = z2[j] - z1; total += n2[j] * (z2[j] - z1)
                    else:
                        mx = max(rv[j], nm[i]); z2[j] = min((n1 - mx) / usl[j] + z1, ZUP[i]); dz[j] = z2[j] - z1; n2[j] = n1 - dz[j] * usl[j]
                        total += dz[j] * (n1 + n2[j]) / 2.0
                    za += 0.1
                    if m1:
                        mask = False
                else:
                    za += 0.1
                z1 = z2[j]; n1 = n2[j]
                if not mask:
                    break
            # ---- restoration of the Annex A band completion (the F-05 fix) ----
            if mask and z2[zup_ea[i] - 1] < ZUP[i]:
                fixes += 1
                zz = z2[zup_ea[i] - 1]; nn = n2[zup_ea[i] - 1]
                while True:
                    if st.r8(nn) <= st.r8(nm[i]):
                        total += nm[i] * (ZUP[i] - zz); nn = nm[i]; zz = ZUP[i]; break
                    idx = st.rns_index(nn, True); u = uv(idx, i); mx = max(RNS[idx], nm[i])
                    zn = min((nn - mx) / u + zz, ZUP[i]); d = zn - zz; nnew = nn - d * u
                    total += d * (nn + nnew) / 2.0; zz = zn; nn = nnew
                    if zz >= ZUP[i]:
                        break
                z2[zup_ea[i] - 1] = zz; n2[zup_ea[i] - 1] = nn
            z1 = z2[zup_ea[i] - 1]; n1 = n2[zup_ea[i] - 1]
            if lastm:
                idx = st.rns_index(n2[lastj], True); rv[lastj] = RNS[idx]; usl[lastj] = uv(idx, i)
    if total < 0:
        total = 0
    return total, fixes


def c_eps0_t64(core):
    saveZ, saveR, saveU = st.ZUPc, st.RNSc, st.USLc
    st.ZUPc, st.RNSc, st.USLc = st.ZUP, st.RNS, st.USL22
    try:
        return st.c_slopes(core, eps=0.0)[0]
    finally:
        st.ZUPc, st.RNSc, st.USLc = saveZ, saveR, saveU


def tw(x):
    """Independent re-implementation of f_temporal_weight_loudness / f_lowpass_intp."""
    def lp(x, tau):
        a1 = math.exp(-1 / (2000 * 24 * tau)); b0 = 1 - a1; y1 = 0.0; out = np.empty_like(x); n = len(x)
        for i in range(n):
            x0 = x[i]; y1 = b0 * x0 + a1 * y1; out[i] = y1
            if i < n - 1:
                xd = (x[i + 1] - x0) / 24.0
                for k in range(1, 24):
                    x0 += xd; y1 = b0 * x0 + a1 * y1
        return out
    return 0.47 * lp(x, 3.5e-3) + 0.53 * lp(x, 70e-3)


K = {18: 4332, 23: 5100, 24: 4800, 25: 5100}

if __name__ == "__main__":
    for sig in (18, 23, 24, 25):
        d = f"{st.ROOT}/signal-{sig}"
        nl = st.rd(f"{d}/R-pipeline/nl.bin"); n = len(nl) // 21; nl = nl.reshape(21, n)
        raw22 = st.rd(f"{d}/R-pipeline/slope_raw22.bin"); cs = st.rd(f"{d}/C-slope-on-Rnl-total.bin")
        k = K[sig]
        cvar = np.array([c_eps0_t64(list(nl[:, t])) for t in range(k + 1)])
        sparse = np.nonzero(np.abs(raw22[:k + 1] - cvar) > 1e-6)[0]
        fixed = np.empty(k + 1); nfix = np.zeros(k + 1, dtype=int)
        for t in range(k + 1):
            fixed[t], nfix[t] = rust_slopes_fixed(list(nl[:, t]), st.USL22)
        sparse_with_fix = int((nfix[sparse] > 0).sum())
        nonsparse_fix = int(((nfix > 0) & (np.abs(raw22[:k + 1] - cvar) <= 1e-6)).sum())
        resid = np.abs(fixed - cvar)
        print(f"sig {sig}: sparse frames (|raw22-C(eps0,f64)|>1e-6) = {len(sparse)}; of these with restoration triggered = {sparse_with_fix}; "
              f"non-sparse frames where restoration triggered = {nonsparse_fix}; total frames with restoration = {int((nfix>0).sum())}")
        print(f"         fixed-Rust vs C(eps0,f64): max |diff| = {resid.max():.3e}; frames >1e-12: {int((resid>1e-12).sum())}; frames >1e-13: {int((resid>1e-13).sum())}")
        t_raw22 = tw(raw22[:k + 1])[k]; t_fixed = tw(fixed)[k]; t_cvar = tw(cvar)[k]; t_c = tw(cs[:k + 1])[k]
        print(f"         tail @K: Rust raw22={t_raw22:.17g}  Rust fixed={t_fixed:.17g}  C(eps0,f64)={t_cvar:.17g}  C official-slopes={t_c:.17g}")
        print(f"         tail diffs: raw22-C_official={t_raw22-t_c:+.3e}; fixed-C(eps0,f64)={t_fixed-t_cvar:+.3e}; fixed-C_official={t_fixed-t_c:+.3e}; C(eps0,f64)-C_official={t_cvar-t_c:+.3e}")
        if len(sparse):
            t = int(sparse[0]); print(f"         example sparse frame {t}: raw22={raw22[t]:.10f} fixed={fixed[t]:.10f} C(eps0,f64)={cvar[t]:.10f} restorations={nfix[t]}")
