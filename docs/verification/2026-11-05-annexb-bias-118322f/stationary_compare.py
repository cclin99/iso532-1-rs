"""Official C CLI (stationary and time-varying steady state) vs Annex B.3 workbook N for signals 2-5."""
import json, re, sys, pathlib, numpy as np
ROOT = pathlib.Path(sys.argv[1]); W = ROOT / "tmp/bias-2026-11-05/run2"
comp = json.load(open(ROOT / "docs/verification/2026-11-05-perf-compliance-118322f/compliance-v0.4.0.json", encoding="utf-8"))
OUTD = ROOT / "tmp/acceptance-040-astra/contracts-output-candidate"
res = {}
for s in (2, 3, 4, 5):
    ref = comp["points"][str(s)]["n"]["ref"]
    st = W / f"sig{s}-Stationary/Loudness.csv"
    c_st = float(re.search(r"N / sone \(free field\);\s*([\d.]+)", st.read_text()).group(1))
    tv = [l.split(";") for l in (W / f"sig{s}-Time_varying/Loudness.csv").read_text().splitlines() if re.match(r"^\d", l)]
    t = np.array([float(a) for a, b in tv]); n = np.array([float(b) for a, b in tv])
    m = (t >= 2.0) & (t <= t.max() - 1.0)         # steady part, away from onset and the end
    c_tv = float(np.median(n[m]))
    rust_zwst = comp["points"][str(s)]["n"]["got"]
    # Rust zwtv steady state from the Astra output of the same calibrated input (zwtv on a stationary file)
    res[s] = {"workbook_N": ref, "official_c_stationary": c_st, "official_c_time_varying_steady_median": c_tv,
              "c_stationary_vs_wb_pct": (c_st / ref - 1) * 100, "c_tv_vs_wb_pct": (c_tv / ref - 1) * 100,
              "rust_zwst_mosqito_front_end": rust_zwst, "rust_zwst_vs_wb_pct": (rust_zwst / ref - 1) * 100}
json.dump(res, open(ROOT / "tmp/bias-2026-11-05/stationary-compare.json", "w"), indent=1)
for s, r in res.items():
    print(s, f"wb {r['workbook_N']:.4f} | C stat {r['official_c_stationary']:.4f} ({r['c_stationary_vs_wb_pct']:+.3f}%) | C tv steady {r['official_c_time_varying_steady_median']:.4f} ({r['c_tv_vs_wb_pct']:+.3f}%) | Rust zwst {r['rust_zwst_mosqito_front_end']:.4f} ({r['rust_zwst_vs_wb_pct']:+.3f}%)")
