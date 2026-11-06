"""Reproduce Astra 2026-11-05 'downstream residual' (iso532 slopes vs official C on identical
28-band Annex levels, signals 2-5) with the factor port: is it the ZUP band-edge constant (F2)?"""
import json, subprocess, sys, pathlib
import numpy as np
sys.path.insert(0, str(pathlib.Path("../factor-2026-11-06").resolve()))
from slopes_port import Slopes
A = pathlib.Path("../../docs/verification/2026-11-05-F03-filter-independent-118322f")
ctrl = json.load(open(A / "c-fullprecision-controls.json"))
cases = []
for l in open(A / "frontend-results.jsonl.txt"):
    r = json.loads(l)
    if r.get("frontend") == "annex" and r.get("skip_samples") == 9600 and "levels" in r:
        cases.append(r)
inp = "\n".join(" ".join(repr(x) for x in r["levels"]) for r in cases) + "\n"
out = subprocess.run([str(pathlib.Path("levels2core/target/release/levels2core.exe").resolve())], input=inp, capture_output=True, text=True, check=True).stdout.splitlines()
res = []
for r, line in zip(cases, out):
    v = [float(x) for x in line.split()]
    core, n_iso, sp_iso = np.array(v[:21]), v[21], np.array(v[22:])
    c = ctrl[str(r["signal"])][r["calibration"]]["022"]
    row = {"signal": r["signal"], "cal": r["calibration"],
           "iso532_vs_astra_candidate_N": n_iso - r["n"],
           "iso532_vs_astra_candidate_Nprime_max": float(np.max(np.abs(sp_iso - np.array(r["specific"])))),
           "nm0": core[0]}
    bark = c["specific_max_error_bark"]; k = int(round(bark * 10)) - 1
    for lab, s in (("port_022_e0", Slopes(0.22, 0.0)), ("port_022_e1e-4", Slopes(0.22, 1e-4)), ("port_022_e1e-4_f32", Slopes(0.22, 1e-4, True))):
        n, sp, _ = s.frame(core, True)
        row[lab + "_minus_C_N"] = n - c["same_levels_c_n"]
        row[lab + "_Nprime_at_bark_minus_C"] = sp[k] - c["specific_max_error_c"]
    row["iso532_minus_C_N"] = n_iso - c["same_levels_c_n"]
    row["iso532_Nprime_at_bark_minus_C"] = sp_iso[k] - c["specific_max_error_c"]
    row["bark"] = bark
    row["local_slope_x_1e-4"] = (sp_iso[k - 1] - sp_iso[k + 1]) / 0.2 * 1e-4 if 0 < k < 239 else None
    res.append(row)
for row in res:
    print({k: (f"{v:.3e}" if isinstance(v, float) else v) for k, v in row.items()})
json.dump(res, open("astra_residual.json", "w"), indent=1)
