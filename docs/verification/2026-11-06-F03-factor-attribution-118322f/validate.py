"""Validation of slopes_port.py: eps = 0 must reproduce iso532 0.4.0 from its own nonlinear-decay
output; eps = 1e-4 must reproduce SQAT v2.0 (2026-11-05 Octave run). Signal 1 from the levels."""
import numpy as np, pathlib
from slopes_port import Slopes, tv_pipeline
R = pathlib.Path('out/rust'); O = pathlib.Path('<REPO>/tmp/impl-2026-11-05/out')
nm = np.fromfile(R / 's22-sig1-nm.bin', '<f8')
for usl, eps, f in [(0.24, 0, False), (0.24, 1e-4, False), (0.22, 1e-4, False), (0.22, 1e-4, True), (0.24, 0, True)]:
    n, sp, k = Slopes(usl, eps, f).frame(nm, True); print(f"sig1 usl={usl} eps={eps} f32={f}: N={n:.10f} grid_samples={k}")
print("sig1 refs: iso532", np.fromfile(O / 'rust_0.24-sig1-n.bin', '<f8')[0], "SQAT", np.fromfile(O / 'sqat_0.24-sig1-n.bin', '<f8')[0], "official C CLI 83.2957, workbook 83.2957")
n0, sp0, _ = Slopes(0.24, 0, False).frame(nm, True); n1, sp1, _ = Slopes(0.24, 1e-4, False).frame(nm, True)
print("sig1 N': port eps=1e-4 vs SQAT max", np.abs(np.array(sp1) - np.fromfile(O / 'sqat_0.24-sig1-sp.bin', '<f8')).max(),
      "| port eps=0 vs iso532 max", np.abs(np.array(sp0) - np.fromfile(O / 'rust_0.24-sig1-sp.bin', '<f8')).max(), "(C-style sampler without the constant skips grid samples; iso532 rounds to 1e-8 instead)")
for s in range(6, 26):
    nl = np.fromfile(R / f's22-sig{s}-zero-nl.bin', '<f8'); nl = nl.reshape(21, len(nl) // 21)
    n_e0, sp_e0, _ = tv_pipeline(nl, Slopes(0.24, 0, False), want_spec=True)
    rn = np.fromfile(R / f's22-sig{s}-zero-n.bin', '<f8'); rsp = np.fromfile(R / f's22-sig{s}-zero-sp.bin', '<f8').reshape(240, -1)
    n_e1, sp_e1, _ = tv_pipeline(nl, Slopes(0.24, 1e-4, False), want_spec=True)
    qn = np.fromfile(O / f'sqat_0.24-sig{s}-n.bin', '<f8'); qsp = np.fromfile(O / f'sqat_0.24-sig{s}-sp.bin', '<f8').reshape(240, -1); L = min(len(qn), len(n_e1))
    print(f"sig{s:2d} n_time={nl.shape[1]:6d} | eps=0 vs iso532: N max {np.abs(n_e0 - rn).max():.2e} | eps=1e-4 vs SQAT 0.24: N max {np.abs(n_e1[:L] - qn[:L]).max():.2e} N' max {np.abs(sp_e1[:, :L] - qsp[:, :L]).max():.2e} (frames port {len(n_e1)} SQAT {len(qn)})")
