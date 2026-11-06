"""Cross-check of the Claude factor-attribution round (2026-11-06) against the three Astra rounds
(2026-11-05 filter-independent, 2026-11-06 three-implementations, 2026-11-06 factorial-matrix).
Reads Astra's delivered machine-readable files and the Claude round's results / cell outputs; writes
crosscheck.json. Run from this folder with the factor-attribution working folder next to it."""
import json, sys, pathlib, warnings
import numpy as np
warnings.filterwarnings("ignore")
HERE = pathlib.Path(__file__).resolve().parent
FA = HERE.parent / "factor-2026-11-06"
sys.path.insert(0, str(FA))
from refs import load_refs
from analyze import at_ref, F
from run_factorial import cell_name
V = pathlib.Path("<REPO>/docs/verification")
FM = V / "2026-11-06-F03-factorial-matrix-118322f"
TI = V / "2026-11-06-F03-three-implementations-118322f"
rf = load_refs()
mine = json.load(open(FA / "results.json"))
canc = json.load(open(FM / "all-tv-cancellation.json"))
paired = json.load(open(FM / "tv-paired-effects.json"))
res = {}

def cell(scale, u, e, s):
    return at_ref(np.load(F / f"{cell_name(scale, 'zero', u, e, False)}-sig{s}-n.npy"), rf[s])

# 1. per-signal max |N - workbook| with USL 0.22 (time-varying 6-25)
cmp = {}
for x in canc:
    s = str(x["signal"]); eng = x["engine"]
    cmp.setdefault(s, {})[f"astra_{eng}_0.22"] = abs(x["max022"]["e022"])
    cmp[s][f"astra_{eng}_0.24"] = abs(x["max024"]["e024"])
for s in cmp:
    cmp[s]["claude_cell_0.22_eps"] = mine["cells"][cell_name("s22", "zero", 0.22, 1e-4, False)]["per_signal"][s]["max_abs"]
    cmp[s]["claude_cell_0.24_eps"] = mine["cells"][cell_name("s22", "zero", 0.24, 1e-4, False)]["per_signal"][s]["max_abs"]
    cmp[s]["claude_sqat_0.22"] = mine["implementations"]["sqat_0.22"]["per_signal"][s]["max_abs"]
    cmp[s]["claude_mosqito_0.22"] = mine["implementations"]["mosqito_0.22"]["per_signal"][s]["max_abs"]
    cmp[s]["claude_mosqito_0.24"] = mine["implementations"]["mosqito_0.24"]["per_signal"][s]["max_abs"]
    cmp[s]["claude_iso532_0.22"] = mine["implementations"]["rust_0.22"]["per_signal"][s]["max_abs"]
res["per_signal_max"] = cmp
d = lambda a, b: max(abs(cmp[s][a] - cmp[s][b]) for s in cmp)
res["per_signal_max_agreement"] = {
    "astra_sqat_vs_claude_cell_0.22_eps": d("astra_sqat_0.22", "claude_cell_0.22_eps"),
    "astra_sqat_vs_claude_sqat_0.22": d("astra_sqat_0.22", "claude_sqat_0.22"),
    "astra_sqat_0.24_vs_claude_cell_0.24_eps": d("astra_sqat_0.24", "claude_cell_0.24_eps"),
    "astra_mos_vs_claude_mosqito_0.22": d("astra_mos_0.22", "claude_mosqito_0.22"),
    "astra_mos_vs_claude_mosqito_0.24": d("astra_mos_0.24", "claude_mosqito_0.24"),
    "astra_c_vs_claude_cell_0.22_eps": d("astra_c_0.22", "claude_cell_0.22_eps"),
}
res["max_over_signals"] = {k: max(cmp[s][k] for s in cmp) for k in next(iter(cmp.values()))}

# 2. where 0.24 improves on 0.22, per engine (Astra counts) and the Claude C-equivalent cell, with magnitudes
tot = {}
for x in canc:
    t = tot.setdefault(x["engine"], dict(points=0, improves=0, worsens=0, unchanged=0))
    t["points"] += x["points"]; t["improves"] += x["024_improves"]; t["worsens"] += x["024_worsens"]; t["unchanged"] += x["unchanged"]
imp, wor, t = [], [], dict(points=0, improves=0, worsens=0, unchanged=0)
for s in range(6, 26):
    a, b = cell("s22", 0.22, 1e-4, s), cell("s22", 0.24, 1e-4, s)
    dd = np.abs(b - rf[s]["N"]) - np.abs(a - rf[s]["N"])
    i, w = dd < -1e-12, dd > 1e-12
    t["points"] += dd.size; t["improves"] += int(i.sum()); t["worsens"] += int(w.sum()); t["unchanged"] += int((~i & ~w).sum())
    imp += list(-dd[i]); wor += list(dd[w])
imp, wor = np.array(imp), np.array(wor)
tot["claude_cell_eps"] = t
res["usl_024_improves_vs_022"] = {"counts": tot, "claude_cell_eps_magnitudes": {
    "improvement_max": float(imp.max()), "improvements_above_1e-4": int((imp > 1e-4).sum()),
    "worsening_max": float(wor.max()), "worsenings_above_1e-4": int((wor > 1e-4).sum())},
    "signal15": {x["engine"]: {k: x[k] for k in ("points", "024_improves", "024_worsens", "unchanged")} for x in canc if x["signal"] == 15}}

# 3. contrasts on the representative signals: USL and calibration x USL (SQAT backend), Claude on workbook points
con = {}
for x in paired:
    if x["outcome"] != "n" or x["contrast"] not in ("USL", "calibration_x_USL"):
        continue
    con.setdefault(f"{x['signal']}", {})[f"astra_{x['backend']}_{x['contrast']}"] = (x["max_abs"], x["max_time_s"])
for s in con:
    si = int(s)
    f1 = cell("s22", 0.24, 1e-4, si) - cell("s22", 0.22, 1e-4, si)
    did = cell("cal", 0.24, 1e-4, si) - cell("cal", 0.22, 1e-4, si) - f1
    k1, k2 = int(np.argmax(np.abs(f1))), int(np.argmax(np.abs(did)))
    con[s]["claude_USL_workbook_points"] = (float(abs(f1[k1])), float(rf[si]["t"][k1]))
    con[s]["claude_calibration_x_USL_workbook_points"] = (float(abs(did[k2])), float(rf[si]["t"][k2]))
res["contrasts_representative"] = con

# 4. three-implementations: baseline maxima against the workbook (Astra report table) vs Claude
res["three_implementations_baselines"] = {
    "astra_sqat_baseline_max": 0.0168838908734, "claude_sqat_0.24_max": mine["implementations"]["sqat_0.24"]["workbook"]["max_abs"],
    "astra_mosqito_tv_max_0.24": 0.0228893512431, "claude_mosqito_0.24_max": mine["implementations"]["mosqito_0.24"]["workbook"]["max_abs"],
    "astra_mosqito_tv_max_0.22": 0.0232840920114, "claude_mosqito_0.22_max": mine["implementations"]["mosqito_0.22"]["workbook"]["max_abs"],
    "note": "Astra values copied from the three-implementations report tables (time-varying 6-25)"}

# 5. Astra 2026-11-05 unexplained downstream residual, reproduced by astra_residual.py
ar = json.load(open(HERE / "astra_residual.json"))
res["astra_2026_11_05_downstream_residual"] = {
    "cases": len(ar),
    "iso532_reproduces_astra_candidate_max_N": max(abs(r["iso532_vs_astra_candidate_N"]) for r in ar),
    "iso532_reproduces_astra_candidate_max_Nprime": max(r["iso532_vs_astra_candidate_Nprime_max"] for r in ar),
    "Nprime_at_bark_iso532_minus_C_max": max(abs(r["iso532_Nprime_at_bark_minus_C"]) for r in ar),
    "Nprime_at_bark_port_eps_minus_C_max": max(abs(r["port_022_e1e-4_Nprime_at_bark_minus_C"]) for r in ar),
    "Nprime_at_bark_port_eps_f32_minus_C_max": max(abs(r["port_022_e1e-4_f32_Nprime_at_bark_minus_C"]) for r in ar),
    "N_iso532_minus_C_max": max(abs(r["iso532_minus_C_N"]) for r in ar),
    "N_port_eps_minus_C_max": max(abs(r["port_022_e1e-4_minus_C_N"]) for r in ar),
    "signal5_N_iso532_minus_C": [r["iso532_minus_C_N"] for r in ar if r["signal"] == 5],
    "signal5_1e-4_x_nm0": [1e-4 * r["nm0"] for r in ar if r["signal"] == 5]}
json.dump(res, open(HERE / "crosscheck.json", "w", newline="\n"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k not in ("per_signal_max", "contrasts_representative")}, indent=1))
print(json.dumps(res["contrasts_representative"], indent=0))
