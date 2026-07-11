"""Binding-overhead check (spec §13).

Compare against a same-day ``cargo bench`` zwtv number on this machine.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from iso532_testkit import contract_signal

import iso532

FS = 48000
sig = contract_signal(10 * FS)

iso532.loudness_zwtv(sig, float(FS))
best = float("inf")
for _ in range(20):
    t0 = time.perf_counter()
    iso532.loudness_zwtv(sig, float(FS))
    best = min(best, time.perf_counter() - t0)
print(f"binding zwtv 10s best-of-20: {best * 1e3:.1f} ms")
