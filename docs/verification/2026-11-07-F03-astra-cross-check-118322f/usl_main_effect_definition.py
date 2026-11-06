"""Astra's USL main effect is the mean over both calibrations of the signed (0.24 - 0.22) N difference;
the Claude F1 numbers are at 2*sqrt(2). Recompute Astra's definition from the Claude cells."""
import json, sys, pathlib, warnings
import numpy as np
warnings.filterwarnings("ignore")
FA = pathlib.Path(__file__).resolve().parent.parent / "factor-2026-11-06"
sys.path.insert(0, str(FA))
from refs import load_refs
from analyze import at_ref, F
from run_factorial import cell_name
rf = load_refs()
cc = json.load(open(pathlib.Path(__file__).resolve().parent / "crosscheck.json"))["contrasts_representative"]
out = {}
for s in (6, 15, 16, 25):
    c = lambda sc, u: at_ref(np.load(F / f"{cell_name(sc, 'zero', u, 1e-4, False)}-sig{s}-n.npy"), rf[s])
    m = 0.5 * ((c("s22", 0.24) - c("s22", 0.22)) + (c("cal", 0.24) - c("cal", 0.22)))
    k = int(np.argmax(np.abs(m)))
    out[s] = {"claude_mean_over_calibration": [float(abs(m[k])), float(rf[s]["t"][k])], "astra_sqat_USL": cc[str(s)]["astra_sqat_USL"]}
    print(s, out[s])
json.dump(out, open("usl_main_effect_definition.json", "w", newline="\n"), indent=1)
