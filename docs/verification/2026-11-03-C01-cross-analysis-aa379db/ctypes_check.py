"""Official C f_calc_slopes (unmodified ISO_532-1.c through Astra's stage wrapper DLL, rc_slopes with
n = 1) on synthetic core-loudness frames; pairs with band0_real-main.rs.txt which calls the real crate.
Requires C01_WORK."""
import ctypes
import os
import sys

import numpy as np

ROOT = os.environ.get("C01_WORK")
if not ROOT:
    sys.exit("set C01_WORK")
dll = ctypes.CDLL(f"{ROOT}/c/stages.dll")
dll.rc_slopes.restype = ctypes.c_int
P = ctypes.POINTER(ctypes.c_double)
dll.rc_slopes.argtypes = [P, ctypes.c_int, P, P]


def c_total(nm):
    nl = np.ascontiguousarray(np.array(nm, dtype=np.float64))  # [21, n=1]
    total = np.zeros(1); spec = np.zeros(240)
    rc = dll.rc_slopes(nl.ctypes.data_as(P), 1, total.ctypes.data_as(P), spec.ctypes.data_as(P))
    assert rc == 0
    return total[0], spec


def mk(nm0, nm20, fill=0.0):
    a = [fill] * 21; a[0] = nm0; a[20] = nm20; return a


for name, nm in [("nm0=0.5 nm20=1.0", mk(0.5, 1.0)), ("nm0=0.5 nm20=0.3", mk(0.5, 0.3)), ("nm0=0.0 nm20=1.0", mk(0.0, 1.0)),
                 ("nm0=0.2 nm20=2.0", mk(0.2, 2.0)), ("nm0=1.0 nm20=1.0", mk(1.0, 1.0)), ("all0.3 nm0=0.5 nm20=1.0", mk(0.5, 1.0, 0.3))]:
    t, spec = c_total(nm)
    print(f"official C: {name}: total={t:.9f} bits={np.float64(t).view(np.uint64):016x} spec[0..9]={[f'{v:.4f}' for v in spec[:9]]}")
