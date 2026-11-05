"""Hypothesis test: recompute with the fixed scale 2*sqrt(2) Pa per full-scale unit instead of the
calibration-file factor, and compare Nmax / N5 / per-point ratios with the workbooks."""
import json, re, sys, pathlib, numpy as np, openpyxl, iso532, importlib.metadata as md
ROOT = pathlib.Path(sys.argv[1]); INP = ROOT / "tmp/acceptance-040-astra/contracts-inputs"
astra = json.load(open(ROOT / "docs/verification/2026-11-04-release-0.4.0-fca4ccd/contracts/contracts-results.json", encoding="utf-8"))
F_CAL = astra["input_hashes"]["calibration_factor"]; F_FIX = 2 * np.sqrt(2)
scale = F_FIX / F_CAL
res = {"wheel": md.version("iso532"), "calibration_factor": F_CAL, "fixed_factor": F_FIX, "scale": scale,
       "scale_dB": 20 * np.log10(scale), "time_varying": {}, "stationary": {}}
for wb in sorted((ROOT / "tmp/c01-material/official").rglob("*.xlsx")):
    w = openpyxl.load_workbook(wb, data_only=True, read_only=True)
    for sh in w:
        s = int(re.search(r"\d+", sh.title).group())
        if s == 1:
            continue
        rows = list(sh.values)
        x = np.fromfile(INP / f"sig{s}.bin", "<f8")
        if s <= 5:
            ref = float(rows[7][1])
            out = {"ref": ref}
            for tag, sig in (("cal", x), ("fixed", x * scale)):
                n, _, _, t = iso532.loudness_zwtv(sig, 48000.0, "free")
                n = np.asarray(n); t = np.asarray(t)
                out[f"zwtv_steady_{tag}"] = float(np.median(n[(t >= 2) & (t <= t[-1] - 1)]))
                out[f"zwtv_steady_{tag}_pct"] = (out[f"zwtv_steady_{tag}"] / ref - 1) * 100
            res["stationary"][s] = out
            continue
        data = [r for r in rows[10:] if isinstance(r[0], (int, float)) and isinstance(r[1], (int, float))]
        t_ref = np.array([r[0] for r in data]); n_ref = np.array([r[1] for r in data], float)
        idx = np.rint(t_ref * 500).astype(int)
        nmax_ref = float(rows[4][1]); n5_ref = float(rows[5][1])
        out = {"nmax_ref": nmax_ref, "n5_ref": n5_ref}
        field = "diffuse" if s == 15 else "free"
        for tag, sig in (("cal", x), ("fixed", x * scale)):
            n = np.asarray(iso532.loudness_zwtv(sig, 48000.0, field)[0])
            g = n[idx]; m = n_ref >= 0.5
            out[f"point_median_pct_{tag}"] = float(np.median(g[m] / n_ref[m] - 1) * 100)
            out[f"nmax_pct_{tag}"] = (n.max() / nmax_ref - 1) * 100
            tol = np.maximum(0.1, 0.05 * n_ref)
            out[f"points_outside_{tag}"] = int(np.sum(np.abs(g - n_ref) > tol))
        res["time_varying"][s] = out
json.dump(res, open(sys.argv[2], "w"), indent=1)
print(f"scale {scale:.6f} = {res['scale_dB']:+.4f} dB")
for s, o in res["stationary"].items():
    print(f"st {s:>2} zwtv steady: cal {o['zwtv_steady_cal_pct']:+.3f}%  fixed {o['zwtv_steady_fixed_pct']:+.3f}%")
for s, o in res["time_varying"].items():
    print(f"tv {s:>2} N(t) median: cal {o['point_median_pct_cal']:+.3f}% -> fixed {o['point_median_pct_fixed']:+.3f}% | Nmax cal {o['nmax_pct_cal']:+.3f}% -> fixed {o['nmax_pct_fixed']:+.3f}% | outside {o['points_outside_cal']}/{o['points_outside_fixed']}")
