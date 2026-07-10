"""Binding-overhead check (spec §13).

Compare against a same-day ``cargo bench`` zwtv number on this machine.
"""

import time

import numpy as np

import iso532

FS = 48000
i = np.arange(10 * FS, dtype=np.uint64)
sig = (
    ((i * np.uint64(2654435761)) % np.uint64(96001)).astype(np.float64)
    / 96000.0
    * 0.02
    - 0.01
)

iso532.loudness_zwtv(sig, float(FS))
best = float("inf")
for _ in range(20):
    t0 = time.perf_counter()
    iso532.loudness_zwtv(sig, float(FS))
    best = min(best, time.perf_counter() - t0)
print(f"binding zwtv 10s best-of-20: {best * 1e3:.1f} ms")
