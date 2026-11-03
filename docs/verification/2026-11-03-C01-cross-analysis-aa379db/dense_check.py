"""Separate the dense small per-frame slope differences (1e-10..1e-6) from the sparse large ones:
re-run the C port with epsilon = 0 and binary64 tables. Requires C01_WORK."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import slope_trace as st  # noqa: E402


def c_slopes_var(core, eps, tables64):
    saveZ, saveR, saveU = st.ZUPc, st.RNSc, st.USLc
    if tables64:
        st.ZUPc, st.RNSc, st.USLc = st.ZUP, st.RNS, st.USL22
    try:
        return st.c_slopes(core, eps=eps)[0]
    finally:
        st.ZUPc, st.RNSc, st.USLc = saveZ, saveR, saveU


if __name__ == "__main__":
    for sig in (18, 23, 24, 25):
        d = f"{st.ROOT}/signal-{sig}"
        nl = st.rd(f"{d}/R-pipeline/nl.bin"); n = len(nl) // 21; nl = nl.reshape(21, n)
        raw22 = st.rd(f"{d}/R-pipeline/slope_raw22.bin")
        K = {18: 4332, 23: 5100, 24: 4800, 25: 5100}[sig]
        stats = {}
        for label, eps, t64 in [("orig", st.EPS, False), ("eps0", 0.0, False), ("eps0+tables64", 0.0, True)]:
            diffs = np.array([raw22[k] - c_slopes_var(list(nl[:, k]), eps, t64) for k in range(K + 1)])
            ad = np.abs(diffs)
            stats[label] = (int((ad > 1e-12).sum()), int((ad > 1e-10).sum()), int((ad > 1e-6).sum()), int((ad > 1e-4).sum()), float(ad.max()))
        print(f"sig {sig}: frames 0..{K}; raw22 - C-variant: (n>1e-12, n>1e-10, n>1e-6, n>1e-4, max)")
        for label, s in stats.items():
            print(f"   {label:14s}: {s}")
        diffs = np.array([raw22[k] - c_slopes_var(list(nl[:, k]), 0.0, True) for k in range(K + 1)])
        nz = np.nonzero(diffs)[0]
        print(f"   eps0+tables64: frames with nonzero diff: {len(nz)}; first 12: {nz[:12].tolist()}")
        mags = np.abs(diffs[nz])
        print(f"   of those: <=1e-13: {(mags<=1e-13).sum()}  1e-13..1e-6: {((mags>1e-13)&(mags<=1e-6)).sum()}  >1e-6: {(mags>1e-6).sum()}")
