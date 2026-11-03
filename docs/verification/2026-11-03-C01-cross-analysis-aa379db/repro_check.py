"""Reproduce Astra's tail-decomposition values with an independently written temporal weighting
(sliver_check.tw) applied to Astra's stage arrays: baseline Rust = tw(slope_round), remove_R_rounding
= tw(slope_raw), replace_slopes_C = tw(C-slope-on-Rnl-total). Compares against tail-decomposition.csv
of the tail-root-cause delivery. Requires C01_WORK."""
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import slope_trace as st  # noqa: E402
import sliver_check as sc  # noqa: E402

csv_path = Path(__file__).resolve().parent.parent / "2026-11-03-C01-tail-root-cause-aa379db" / "tail-decomposition.csv"
rows = list(csv.DictReader(open(csv_path, encoding="utf-8")))
astra = {(int(r["signal"]), r["intervention"]): (r["tail_decimal17"], r["tail_bits"]) for r in rows}

worst = 0.0
for sig in (18, 23, 24, 25):
    d = f"{st.ROOT}/signal-{sig}"; k = sc.K[sig]
    series = {
        "baseline": st.rd(f"{d}/R-pipeline/slope_round.bin"),
        "remove_R_rounding": st.rd(f"{d}/R-pipeline/slope_raw.bin"),
        "replace_slopes_C": st.rd(f"{d}/C-slope-on-Rnl-total.bin"),
    }
    for step, arr in series.items():
        mine = sc.tw(arr[:k + 1])[k]
        ref_dec, ref_bits = astra[(sig, step)]
        ref = float(ref_dec)
        worst = max(worst, abs(mine - ref))
        print(f"sig {sig} {step:18s}: independent TW = {mine:.17g} bits={np.float64(mine).view(np.uint64):016x} | Astra = {ref_dec} bits={ref_bits} | diff = {mine-ref:+.3e}")
print(f"worst |independent TW - Astra| over 12 tail values = {worst:.3e}")
