"""Main-loudness stage: do the C program's float32-promoted constants (.0635f, 0.4f, 0.32f, A0[], DCB[])
explain the whole Rust-vs-C core-loudness difference on the same third-octave history?
Requires C01_WORK."""
import math
import os
import sys

import numpy as np

ROOT = os.environ.get("C01_WORK")
if not ROOT:
    sys.exit("set C01_WORK to the tail-root-cause scratch directory")
RAP = [45.0, 55.0, 65.0, 71.0, 80.0, 90.0, 100.0, 120.0]
DLL = [[-32, -24, -16, -10, -5, 0, -7, -3, 0, -2, 0], [-29, -22, -15, -10, -4, 0, -7, -2, 0, -2, 0], [-27, -19, -14, -9, -4, 0, -6, -2, 0, -2, 0],
       [-25, -17, -12, -9, -3, 0, -5, -2, 0, -2, 0], [-23, -16, -11, -7, -3, 0, -4, -1, 0, -1, 0], [-20, -14, -10, -6, -3, 0, -4, -1, 0, -1, 0],
       [-18, -12, -9, -6, -2, 0, -3, -1, 0, -1, 0], [-15, -10, -8, -4, -2, 0, -3, -1, 0, -1, 0]]
DLL = [[float(v) for v in r] for r in DLL]
LTQ = [30.0, 18.0, 12.0, 8.0, 7.0, 6.0, 5.0, 4.0] + [3.0] * 12
A0 = [0.0] * 10 + [-0.5, -1.6, -3.2, -5.4, -5.6, -4.0, -1.5, 2.0, 5.0, 12.0]
DCB = [-0.25, -0.6, -0.8, -0.8, -0.5, 0.0, 0.5, 1.1, 1.5, 1.7, 1.8, 1.8, 1.7, 1.6, 1.4, 1.2, 0.8, 0.5, 0.0, -0.5]
f32 = lambda v: float(np.float32(v))


def main_port(spec, k0635_f32, tables_f32, k04_f32, c_korry_compare):
    a0 = [f32(v) for v in A0] if tables_f32 else A0
    dcb = [f32(v) for v in DCB] if tables_f32 else DCB
    k = f32(0.0635) if k0635_f32 else 0.0635
    k4 = f32(0.4) if k04_f32 else 0.4
    k32 = f32(0.32) if k04_f32 else 0.32
    ti = [0.0] * 11
    for b in range(11):
        row = 0
        while row < 7 and spec[b] > RAP[row] - DLL[row][b]:
            row += 1
        ti[b] = 10.0 ** ((spec[b] + DLL[row][b]) / 10.0)
    gi = [sum(ti[0:6]), sum(ti[6:9]), sum(ti[9:11])]
    lcb = [10.0 * math.log10(g) if g > 0 else 0.0 for g in gi]
    nm = [0.0] * 21
    for b in range(20):
        le = (lcb[b] if b < 3 else spec[b + 8]) - a0[b]
        if le > LTQ[b]:
            le -= dcb[b]
            mp1 = k * 10.0 ** (0.025 * LTQ[b])
            mp2 = (1.0 - 0.25 + 0.25 * 10.0 ** (0.1 * (le - LTQ[b]))) ** 0.25 - 1.0
            nm[b] = max(mp1 * mp2, 0.0)
    korry = k4 + k32 * nm[0] ** 0.2
    if (korry < 1.0) if c_korry_compare else (korry <= 1.0):
        nm[0] *= korry
    return nm


def rd(p):
    return np.fromfile(p, dtype='<f8')


if __name__ == "__main__":
    for sig in (18, 23, 24, 25):
        d = f"{ROOT}/signal-{sig}"
        tol = rd(f"{d}/R-pipeline/tol.bin"); n = len(tol) // 28; tol = tol.reshape(28, n)
        rcore = rd(f"{d}/R-pipeline/core.bin").reshape(21, n)
        ccore = rd(f"{d}/C-core-on-Rtol.bin").reshape(21, n)
        variants = {
            "port(f64) vs Rust core": ((False, False, False, False), rcore),
            "port(C-style: .0635f+0.4f/0.32f+A0/DCB f32) vs C core": ((True, True, True, True), ccore),
            "only .0635f vs C core": ((True, False, False, True), ccore),
            "only A0/DCB f32 vs C core": ((False, True, False, True), ccore),
            ".0635f + A0/DCB f32 vs C core": ((True, True, False, True), ccore),
        }
        print(f"sig {sig}: native Rust-C core max |diff| = {np.abs(rcore-ccore).max():.2e}")
        for label, (args, ref) in variants.items():
            out = np.empty((21, n))
            for t in range(n):
                out[:, t] = main_port(list(tol[:, t]), *args)
            print(f"   {label:58s}: max |diff| = {np.abs(out-ref).max():.2e}; bitwise mismatches = {int((out.view('u8')!=ref.view('u8')).sum())}/{out.size}")
