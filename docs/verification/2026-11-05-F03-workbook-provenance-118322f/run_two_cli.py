"""Run the official CLI built unmodified (USL[12][4]=0.22f) and with only that cell set to 0.24f on the
2*sqrt(2)-scaled float WAVs, then compare both with the Annex B workbooks point by point (4-decimal output)."""
import subprocess, re, sys, json, pathlib, hashlib, numpy as np, openpyxl
ROOT = pathlib.Path(sys.argv[1]); U = ROOT / "tmp/usl-2026-11-05"; OFF = ROOT / "tmp/c01-material/official"
sha = lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
res = {"cli": {}, "signals": {}}
for v in ("v022", "v024"):
    exe = U / f"build/{v}/cli.exe"; res["cli"][v] = {"exe_sha256": sha(exe), "source_sha256": sha(U / f"build/{v}/ISO_532-1.c")}
    for s in range(2, 26):
        d = U / f"cli-{v}/sig{s}"; d.mkdir(parents=True, exist_ok=True)
        f = "D" if s == 15 else "F"; wav = str(U / f"wav/sig{s}.wav")
        args = [str(exe), "Stationary", f, wav, "0.2"] if s <= 5 else [str(exe), "Time_varying", f, wav]
        p = subprocess.run(args, cwd=d, capture_output=True); assert p.returncode == 0, (v, s, p.stdout)
def tv(v, s):
    rows = [l.split(";") for l in (U / f"cli-{v}/sig{s}/Loudness.csv").read_text().splitlines() if re.match(r"^\d", l)]
    return np.array([float(a) for a, _ in rows]), np.array([float(b) for _, b in rows])
def spec_rows(v, s):
    return [[float(x) for x in l.split(";") if x.strip()] for l in (U / f"cli-{v}/sig{s}/SpecLoudness.csv").read_text().splitlines() if re.match(r"^\d", l)]
# control: the fresh unmodified build must reproduce the earlier reference_cli.exe output files byte for byte
res["control_v022_equals_reference_cli"] = all((U / f"cli-v022/sig{s}/{n}").read_bytes() == (U / f"cli/sig{s}/{n}").read_bytes()
                                               for s in range(2, 26) for n in ("Loudness.csv", "SpecLoudness.csv"))
tot = {"points": 0, "differ": 0, "wb_eq_022": 0, "wb_eq_024": 0, "wb_eq_neither": 0}
for wb in sorted(OFF.rglob("*.xlsx")):
    w = openpyxl.load_workbook(wb, data_only=True, read_only=True)
    for sh in w:
        s = int(re.search(r"\d+", sh.title).group())
        if s == 1: continue
        rows = list(sh.values)
        if s <= 5:
            ref = {"N": [float(rows[7][1])], "Nspec": [float(r[6]) for r in rows[7:247]]}
            got = {}
            for v in ("v022", "v024"):
                txt = (U / f"cli-{v}/sig{s}/Loudness.csv").read_text()
                got[v] = {"N": [float(re.search(r"N / sone \((?:free|diffuse) field\);\s*([\d.]+)", txt).group(1))],
                          "Nspec": np.array(spec_rows(v, s)).ravel()[-240:].tolist()}
            pairs = [(k, np.array(ref[k]), np.array(got["v022"][k]), np.array(got["v024"][k])) for k in ("N", "Nspec")]
        else:
            data = [r for r in rows[10:] if isinstance(r[0], (int, float)) and isinstance(r[1], (int, float))]
            t_ref = np.round(np.array([r[0] for r in data]), 4); n_ref = np.array([r[1] for r in data], float)
            pairs = []
            vals = {}
            for v in ("v022", "v024"):
                t, n = tv(v, s); i = np.searchsorted(np.round(t, 4), t_ref); assert np.allclose(t[i], t_ref); vals[v] = n[i]
            pairs.append(("N(t)", n_ref, vals["v022"], vals["v024"]))
        o = {}
        for k, r, a, b in pairs:
            dif = np.abs(a - b) > 5e-5
            e22 = np.abs(a - r) < 5e-5; e24 = np.abs(b - r) < 5e-5
            o[k] = {"points": int(len(r)), "v022_exact": int(e22.sum()), "v024_exact": int(e24.sum()),
                    "v022_max_abs": float(np.max(np.abs(a - r))), "v024_max_abs": float(np.max(np.abs(b - r))),
                    "points_where_versions_differ": int(dif.sum()),
                    "there_wb_equals_v022": int((dif & e22).sum()), "there_wb_equals_v024": int((dif & e24).sum()),
                    "there_wb_equals_neither": int((dif & ~e22 & ~e24).sum()),
                    "max_abs_v024_minus_v022": float(np.max(np.abs(a - b)))}
            tot["points"] += len(r); tot["differ"] += int(dif.sum()); tot["wb_eq_022"] += int((dif & e22).sum())
            tot["wb_eq_024"] += int((dif & e24).sum()); tot["wb_eq_neither"] += int((dif & ~e22 & ~e24).sum())
        res["signals"][s] = o
res["totals"] = tot
json.dump(res, open(U / "two-cli-compare.json", "w"), indent=1)
print("control v022 == reference_cli:", res["control_v022_equals_reference_cli"])
print("totals:", tot)
for s, o in sorted(res["signals"].items()):
    for k, x in o.items():
        if x["points_where_versions_differ"] or k == "N":
            print(f"{s:2d} {k:6s} pts {x['points']:5d} | exact 0.22 {x['v022_exact']:5d} (max {x['v022_max_abs']:.4f}) | exact 0.24 {x['v024_exact']:5d} (max {x['v024_max_abs']:.4f}) | differ {x['points_where_versions_differ']:5d}: wb=0.22 {x['there_wb_equals_v022']:5d} wb=0.24 {x['there_wb_equals_v024']:3d} neither {x['there_wb_equals_neither']:3d} | max|0.24-0.22| {x['max_abs_v024_minus_v022']:.4f}")
