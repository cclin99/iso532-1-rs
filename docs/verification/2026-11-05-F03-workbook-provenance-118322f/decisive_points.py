"""Restrict the two-CLI comparison to points where the two builds differ by >= 2e-4 sone (beyond 4-decimal rounding)."""
import re, sys, json, pathlib, numpy as np, openpyxl
ROOT = pathlib.Path(sys.argv[1]); U = ROOT / "tmp/usl-2026-11-05"; OFF = ROOT / "tmp/c01-material/official"
def tv(v, s):
    rows = [l.split(";") for l in (U / f"cli-{v}/sig{s}/Loudness.csv").read_text().splitlines() if re.match(r"^\d", l)]
    return np.array([float(a) for a, _ in rows]), np.array([float(b) for _, b in rows])
out = {}; tot = np.zeros(4, int)
for wb in sorted(OFF.rglob("*time varying*.xlsx")):
    w = openpyxl.load_workbook(wb, data_only=True, read_only=True)
    for sh in w:
        s = int(re.search(r"\d+", sh.title).group()); rows = list(sh.values)
        data = [r for r in rows[10:] if isinstance(r[0], (int, float)) and isinstance(r[1], (int, float))]
        t_ref = np.round(np.array([r[0] for r in data]), 4); n_ref = np.array([r[1] for r in data], float)
        v = {}
        for k in ("v022", "v024"):
            t, n = tv(k, s); v[k] = n[np.searchsorted(np.round(t, 4), t_ref)]
        m = np.abs(v["v024"] - v["v022"]) >= 2e-4 - 1e-9
        if not m.any(): continue
        d22 = np.abs(v["v022"][m] - n_ref[m]); d24 = np.abs(v["v024"][m] - n_ref[m])
        c = [int(m.sum()), int((d22 < 5e-5).sum()), int((d24 < 5e-5).sum()), int((d22 < d24).sum())]
        out[s] = dict(zip(["points", "wb_equals_022", "wb_equals_024", "wb_closer_to_022"], c)); tot += c
out["total"] = dict(zip(["points", "wb_equals_022", "wb_equals_024", "wb_closer_to_022"], tot.tolist()))
json.dump(out, open(U / "decisive-points.json", "w"), indent=1)
for k, o in out.items(): print(k, o)
