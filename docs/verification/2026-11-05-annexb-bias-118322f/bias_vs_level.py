"""Ratio Rust/workbook of N(t) against the reference loudness, per signal (diagnostic for the +0.15% bias)."""
import sys, re, numpy as np, openpyxl, pathlib, json
ROOT = pathlib.Path(sys.argv[1]); OUTD = ROOT / "tmp/acceptance-040-astra/contracts-output-candidate"
off = ROOT / "tmp/c01-material/official"
res = {}
for wb in sorted(off.rglob("*time varying*.xlsx")):
    w = openpyxl.load_workbook(wb, data_only=True, read_only=True)
    for sh in w:
        s = int(re.search(r"\d+", sh.title).group())
        rows = [r for r in list(sh.values)[10:] if isinstance(r[0], (int, float)) and isinstance(r[1], (int, float))]
        t = np.array([r[0] for r in rows]); ref = np.array([r[1] for r in rows], float)
        n = np.fromfile(OUTD / f"sig{s}-n.bin", "<f8")[np.rint(t * 500).astype(int)]
        bins = [(0.3, 1), (1, 2), (2, 4), (4, 8), (8, 16), (16, 64)]
        out = {}
        for lo, hi in bins:
            m = (ref >= lo) & (ref < hi)
            if m.sum() >= 20:
                r = n[m] / ref[m] - 1
                out[f"{lo}-{hi}"] = {"count": int(m.sum()), "median_pct": float(np.median(r) * 100), "p10_pct": float(np.percentile(r, 10) * 100), "p90_pct": float(np.percentile(r, 90) * 100)}
        res[s] = out
json.dump(res, open(sys.argv[2], "w"), indent=1)
for s, o in res.items():
    print(s, "  ".join(f"[{k} sone] {v['median_pct']:+.3f}% (n={v['count']})" for k, v in o.items()))
