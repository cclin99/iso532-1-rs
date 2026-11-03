"""End-to-end: the real Rust `loudness_zwtv` (through Astra's unmodified probe executable, mode
`public`) versus the official C `f_loudness_from_signal` (through Astra's stage wrapper DLL
`rc_public`) on synthetic signals, plus the MoSQITo inheritance check on three sparse frames.
Requires C01_WORK (scratch with probe/target/release/c01-root-probe.exe and c/stages.dll) and
C01_E2E_OUT (an empty scratch directory for the synthetic inputs/outputs)."""
import ctypes
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("C01_WORK", "")); OUT = Path(os.environ.get("C01_E2E_OUT", ""))
if not ROOT.name or not OUT.name:
    sys.exit("set C01_WORK and C01_E2E_OUT")
exe = ROOT / "probe/target/release/c01-root-probe.exe"
dll = ctypes.CDLL(str(ROOT / "c/stages.dll"))
dll.rc_public.restype = ctypes.c_int
P = ctypes.POINTER(ctypes.c_double)
dll.rc_public.argtypes = [P, ctypes.c_int, P, P]
OUT.mkdir(exist_ok=True)
assert exe.exists()


def c_public(x):
    n = len(x) // 24
    tot = np.zeros(n); spec = np.zeros(240 * n)
    rc = dll.rc_public(np.ascontiguousarray(x).ctypes.data_as(P), len(x), tot.ctypes.data_as(P), spec.ctypes.data_as(P))
    assert rc >= 0, rc
    return tot, spec.reshape(240, n)


def rust_public(x, name):
    d = OUT / name; d.mkdir(exist_ok=True)
    x.astype('<f8').tofile(d / "input.bin")
    p = subprocess.run([str(exe), "public", str(d / "input.bin"), str(d)], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    n = np.fromfile(d / "public_n.bin", dtype='<f8'); spec = np.fromfile(d / "public_spec.bin", dtype='<f8').reshape(240, -1)
    return n, spec


rng = np.random.default_rng(1)
fs = 48000; L = 96 * 500  # 1.0 s, multiple of 96 so the grids coincide
t = np.arange(L) / fs


def spl(x):
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) / 20e-6)


def at_60db(x):
    return x * (20e-6 * 10 ** (60 / 20) / np.sqrt(np.mean(x ** 2)))


cases = {}
cases["tone12.5k_60dB"] = at_60db(np.sin(2 * np.pi * 12500 * t))
w = rng.standard_normal(L); W = np.fft.rfft(w); f = np.fft.rfftfreq(L, 1 / fs); W[f < 8000] = 0
cases["noise_gt8k_60dB"] = at_60db(np.fft.irfft(W, L))
cases["white_60dB"] = at_60db(rng.standard_normal(L))
cases["tone1k_60dB"] = at_60db(np.sin(2 * np.pi * 1000 * t))
for name, x in cases.items():
    cn, cspec = c_public(x); rn, rspec = rust_public(x, name)
    m = min(len(cn[::4]), len(rn))  # C internal grid is 2 kHz; the Rust public grid is every 4th frame
    cn4 = cn[::4][:m]; rn = rn[:m]; cs4 = cspec[:, ::4][:, :m]; rs = rspec[:, :m]
    sl = slice(m // 2, m)  # steady-state second half
    print(f"{name:16s} SPL={spl(x):5.1f} dB | N steady mean: C={cn4[sl].mean():.4f} Rust={rn[sl].mean():.4f} (Rust-C={rn[sl].mean()-cn4[sl].mean():+.4f}) | "
          f"max|N diff|={np.abs(rn-cn4).max():.4f} | min specific: C={cs4.min():.3f} Rust={rs.min():.3f} | spec[bark0] steady: Rust={rs[0, sl].mean():.3f} C={cs4[0, sl].mean():.3f}")

from mosqito.sq_metrics.loudness.loudness_zwst._calc_slopes import _calc_slopes  # noqa: E402

nl = np.fromfile(ROOT / "signal-23/R-pipeline/nl.bin", dtype='<f8').reshape(21, -1)
rr = np.fromfile(ROOT / "signal-23/R-pipeline/slope_round.bin", dtype='<f8')
cs = np.fromfile(ROOT / "signal-23/C-slope-on-Rnl-total.bin", dtype='<f8')
for fr in (3893, 4017, 3981):
    N, _ = _calc_slopes(nl[:, fr].copy())
    print(f"mosqito on sig23 frame {fr}: mosqito={float(N):.6f} Rust(rounded,0.24)={rr[fr]:.6f} bitwise_equal={np.float64(N).view(np.uint64)==rr[fr].view(np.uint64)} | official C slopes={cs[fr]:.6f}")
