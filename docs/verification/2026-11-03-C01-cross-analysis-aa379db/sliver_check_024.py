"""Same closure check as sliver_check.py with USL[12][4] = 0.24 kept on both sides (the provisional
project choice), plus the residual against the unmodified official C (0.22f). Requires C01_WORK."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import slope_trace as st  # noqa: E402
import sliver_check as sc  # noqa: E402

f32 = lambda v: float(np.float32(v))


def c_eps0_t64_024(core):
    saveZ, saveR, saveU = st.ZUPc, st.RNSc, st.USLc
    st.ZUPc, st.RNSc, st.USLc = st.ZUP, st.RNS, st.USL  # 0.24 table, binary64, no epsilon
    try:
        return st.c_slopes(core, eps=0.0)[0]
    finally:
        st.ZUPc, st.RNSc, st.USLc = saveZ, saveR, saveU


def c_official_024(core):
    saveZ, saveR, saveU = st.ZUPc, st.RNSc, st.USLc
    st.ZUPc, st.RNSc, st.USLc = st.ZUPc, st.RNSc, [[f32(v) for v in r] for r in st.USL]  # official arithmetic, only the cell changed to 0.24f
    try:
        return st.c_slopes(core)[0]
    finally:
        st.ZUPc, st.RNSc, st.USLc = saveZ, saveR, saveU


if __name__ == "__main__":
    for sig in (18, 23, 24, 25):
        d = f"{st.ROOT}/signal-{sig}"; k = sc.K[sig]
        nl = st.rd(f"{d}/R-pipeline/nl.bin"); n = len(nl) // 21; nl = nl.reshape(21, n)
        cs_official = st.rd(f"{d}/C-slope-on-Rnl-total.bin")[:k + 1]
        fixed24 = np.array([sc.rust_slopes_fixed(list(nl[:, t]), st.USL)[0] for t in range(k + 1)])
        c24 = np.array([c_eps0_t64_024(list(nl[:, t])) for t in range(k + 1)])
        c24off = np.array([c_official_024(list(nl[:, t])) for t in range(k + 1)])
        print(f"sig {sig}: fixed-Rust(0.24) vs C-port(0.24, eps0, f64): per-frame max |diff| = {np.abs(fixed24-c24).max():.2e}")
        t_f = sc.tw(fixed24)[k]; t_c24 = sc.tw(c24)[k]; t_c24off = sc.tw(c24off)[k]; t_off = sc.tw(cs_official)[k]
        print(f"         tail: fixed(0.24)-C(0.24,eps0,f64)={t_f-t_c24:+.2e} | fixed(0.24)-C(official arithmetic, cell 0.24f)={t_f-t_c24off:+.2e} | fixed(0.24)-C(official, 0.22)={t_f-t_off:+.2e}")
        full = np.abs(sc.tw(fixed24) - sc.tw(cs_official)).max()
        print(f"         whole-series weighted max |fixed(0.24) - official C(0.22)| = {full:.2e} sone")
