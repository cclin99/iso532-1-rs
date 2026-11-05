"""Which program produced the Annex B workbooks? Official C CLI (USL[12][4]=0.22f) on float WAVs scaled
2*sqrt(2), and iso532 0.4.0 (0.24) on the same scale, both against the workbook values point by point."""
import re, sys, json, pathlib, numpy as np, openpyxl, iso532, importlib.metadata as md
ROOT = pathlib.Path(sys.argv[1]); U = ROOT / "tmp/usl-2026-11-05"
OFF = ROOT / "tmp/c01-material/official"
def wavf(p):
    b = p.read_bytes(); return np.frombuffer(b[44:], "<f4").astype(np.float64)
def cli_tv(s):
    rows = [l.split(";") for l in (U / f"cli/sig{s}/Loudness.csv").read_text().splitlines() if re.match(r"^\d", l)]
    return np.array([float(a) for a, _ in rows]), np.array([float(b) for _, b in rows])
def cli_spec(s):
    lines = [l for l in (U / f"cli/sig{s}/SpecLoudness.csv").read_text().splitlines() if re.match(r"^\d", l)]
    return [[float(v) for v in l.split(";") if v.strip()] for l in lines]
res = {"wheel": md.version("iso532"), "signals": {}}
for wb in sorted(OFF.rglob("*.xlsx")):
    w = openpyxl.load_workbook(wb, data_only=True, read_only=True)
    for sh in w:
        s = int(re.search(r"\d+", sh.title).group())
        if s == 1: continue
        rows = list(sh.values); x = wavf(U / f"wav/sig{s}.wav")
        field = "diffuse" if s == 15 else "free"
        if s <= 5:
            ref_n = float(rows[7][1]); ref_sp = np.array([float(r[6]) for r in rows[7:247]])
            c_n = float(re.search(r"N / sone \((?:free|diffuse) field\);\s*([\d.]+)", (U / f"cli/sig{s}/Loudness.csv").read_text()).group(1))
            c_sp = np.array(cli_spec(s)).ravel()[-240:] if (U / f"cli/sig{s}/SpecLoudness.csv").exists() else None
            n, sp, _ = iso532.loudness_zwst(x, 48000.0, field)
            res["signals"][s] = {"kind": "stationary", "ref_N": ref_n, "C_N": c_n, "C_equal_ref": abs(c_n - ref_n) < 5e-5,
                                 "C_specific_exact_points": None if c_sp is None else int(np.sum(np.abs(c_sp - ref_sp) < 5e-5)),
                                 "C_specific_max_abs": None if c_sp is None else float(np.max(np.abs(c_sp - ref_sp)))}
            continue
        data = [r for r in rows[10:] if isinstance(r[0], (int, float)) and isinstance(r[1], (int, float))]
        t_ref = np.array([r[0] for r in data]); n_ref = np.array([r[1] for r in data], float)
        t_c, n_c = cli_tv(s)
        ic = np.searchsorted(np.round(t_c, 4), np.round(t_ref, 4)); assert np.allclose(t_c[ic], t_ref)
        c = n_c[ic]
        r = np.asarray(iso532.loudness_zwtv(x, 48000.0, field)[0])[np.rint(t_ref * 500).astype(int)]
        r4 = np.round(r, 4)
        d_c = c - n_ref; d_r = r4 - n_ref
        big = np.abs(r - c) >= 2e-4         # points where 0.24 and 0.22 visibly differ
        o = {"kind": "time_varying", "points": int(len(n_ref)),
             "C_exact": int(np.sum(np.abs(d_c) < 5e-5)), "C_max_abs": float(np.max(np.abs(d_c))),
             "Rust_exact": int(np.sum(np.abs(d_r) < 5e-5)), "Rust_max_abs": float(np.max(np.abs(d_r))),
             "points_where_rust_and_C_differ_ge_2e-4": int(big.sum())}
        if big.any():
            o["at_those_points_ref_closer_to_C"] = int(np.sum(np.abs(d_c[big]) < np.abs(r[big] - n_ref[big])))
            o["at_those_points_ref_closer_to_Rust"] = int(np.sum(np.abs(r[big] - n_ref[big]) < np.abs(d_c[big])))
            o["at_those_points_C_exact"] = int(np.sum(np.abs(d_c[big]) < 5e-5))
            o["at_those_points_Rust_exact"] = int(np.sum(np.abs(d_r[big]) < 5e-5))
            o["max_abs_rust_minus_C"] = float(np.max(np.abs(r - c)))
        res["signals"][s] = o
json.dump(res, open(U / "compare.json", "w"), indent=1)
for s, o in sorted(res["signals"].items()):
    if o["kind"] == "stationary":
        print(f"st {s:2d}: ref {o['ref_N']} C {o['C_N']} equal={o['C_equal_ref']} | C N' exact {o['C_specific_exact_points']}/240 max {o['C_specific_max_abs']}")
    else:
        extra = f" | differ>=2e-4: {o['points_where_rust_and_C_differ_ge_2e-4']} pts, ref closer C {o.get('at_those_points_ref_closer_to_C')} / Rust {o.get('at_those_points_ref_closer_to_Rust')}, exact C {o.get('at_those_points_C_exact')} / Rust {o.get('at_those_points_Rust_exact')}, max|R-C| {o.get('max_abs_rust_minus_C',0):.4f}" if o['points_where_rust_and_C_differ_ge_2e-4'] else ""
        print(f"tv {s:2d}: {o['points']} pts | C exact {o['C_exact']} (max {o['C_max_abs']:.4f}) | Rust exact {o['Rust_exact']} (max {o['Rust_max_abs']:.4f}){extra}")
