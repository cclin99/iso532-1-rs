"""Read-only coordinator cross-checks, independently recomputed from raw evidence."""
from pathlib import Path
import hashlib
import itertools
import json
import numpy as np

ROOT = Path.cwd()
OUT = Path(__file__).resolve().parent
TMP = ROOT / "tmp/verification-f03-factorial-matrix"
PREV = ROOT / "tmp/verification-f03-three-implementations"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


design = read(OUT / "design-matrix.json")
ids = [c["id"] for c in design]
assert len(ids) == len(set(ids)) == 328
primary = [c for c in design if c["domain"] == "stationary"]
fields = ["signal", "frontend", "calibration", "skip_s", "usl", "backend"]
expected = set(itertools.product(
    range(2, 6), ["annex", "noct"], ["sqrt", "cal"], [0, .2],
    ["022", "024"], ["c", "sqat", "mos-round", "mos-noround"]))
assert {tuple(c[k] for k in fields) for c in primary} == expected
assert sum(c["execution"] == "new" for c in design) == 304
assert sum(c["execution"] == "reuse" for c in design) == 24
assert all("skip_s" not in c for c in design if c["domain"] == "timevarying")

previous = {}
for name in ["2026-11-05-F03-filter-independent-118322f",
             "2026-11-06-F03-three-implementations-118322f"]:
    directory = ROOT / "docs/verification" / name
    manifest = read(directory / "delivery-integrity.json")
    for rel, metadata in manifest["files"].items():
        assert sha(directory / rel) == metadata["sha256"], (name, rel)
    previous[name] = {"verified_files": len(manifest["files"]),
                      "manifest_sha256": sha(directory / "delivery-integrity.json")}

for signal in range(2, 26):
    old = np.load(PREV / f"inputs/sig{signal}.npy")
    new = np.load(TMP / f"inputs/sig{signal}-sqrt.npy")
    assert np.array_equal(old.view(np.uint64), new.view(np.uint64))

rounding = []
for usl in ["022", "024"]:
    rel = "mosqito/sq_metrics/loudness/loudness_zwst/_calc_slopes.py"
    baseline = (TMP / f"mos{usl}-round" / rel).read_text(encoding="utf-8")
    diagnostic = (TMP / f"mos{usl}-noround" / rel).read_text(encoding="utf-8")
    for line in ["    N[N <= 16] = floor(N[N <= 16] * 1000 + 0.5) / 1000\n",
                 "    N[N > 16] = floor(N[N > 16] * 100 + 0.5) / 100\n"]:
        assert baseline.count(line) == 1
        baseline = baseline.replace(line, "")
    assert baseline == diagnostic and "    N[N < 0] = 0" in diagnostic
    rounding.append({"usl": usl, "only_two_rounding_lines_removed": True})

levels = read(OUT / "shared-levels.json")
assert len(levels) == 40
for row in levels:
    assert hashlib.sha256(np.array(row["levels"], dtype="<f8").tobytes()).hexdigest() == row["levels_f64_sha256"]

# Directly enumerate matched pairs; do not reuse the verifier's Walsh implementation.
arrays = np.load(TMP / "stationary-python.npz")
effects = read(OUT / "paired-effects.json")
factor_specs = [
    ("frontend", "noct", "annex", "frontend_annex_minus_noct"),
    ("calibration", "sqrt", "cal", "calibration_cal_minus_sqrt"),
    ("skip_s", 0, .2, "skip_0p2_minus_0"),
    ("usl", "022", "024", "usl_024_minus_022")]
paired = []
for signal in range(2, 6):
    cells = [c for c in primary if c["signal"] == signal and c["backend"] == "c"]
    for field, low, high, name in factor_specs:
        differences = []
        for cell in cells:
            if cell[field] != low:
                continue
            mate = next(c for c in cells if c[field] == high and all(
                c[k] == cell[k] for k in fields if k != field))
            differences.append(arrays[mate["id"]][0] - arrays[cell["id"]][0])
        value = float(np.mean(differences))
        reported = next(x for x in effects if x["signal"] == signal
                        and x["backend"] == "c" and x["factors"] == [name])
        residual = abs(value - reported["paired_contrast"]["N_signed"])
        assert residual <= 1e-12
        paired.append({"signal": signal, "factor": name,
                       "direct_pair_mean_sone": value, "table_residual": residual})

tv_results = read(OUT / "tv-cell-results.json")
assert len(tv_results) == 64
assert {x["id"] for x in tv_results} == {x["id"] for x in design if x["domain"] == "timevarying"}
stationary_results = read(OUT / "stationary-cell-results.json")
assert len(stationary_results) == 264
assert {x["id"] for x in stationary_results} == {x["id"] for x in design if x["domain"] != "timevarying"}

refs = read(TMP / "refs.json")
lo = np.load(PREV / "mos022-outputs/sig15.npz")["n"]
hi = np.load(PREV / "mos024-outputs/sig15.npz")["n"]
j = 4803
reference = refs["15"]["n"][j]
point = {"signal": 15, "frame": j, "time_s": j * .002,
         "e022": float(lo[j] - reference),
         "delta024_minus022": float(hi[j] - lo[j]),
         "e024": float(hi[j] - reference)}
assert abs(point["e022"] + point["delta024_minus022"] - point["e024"]) <= 1e-12

result = {"status": "PASS", "kind": "coordinator evidence cross-check, not a second numerical engine run",
          "design_cells": 328, "new_cells": 304, "reused_cells": 24,
          "stationary_cartesian_complete": 256, "prior_delivery_integrity": previous,
          "sqrt_inputs_bitwise_identical_signals": list(range(2, 26)),
          "rounding_source_isolation": rounding, "shared_level_hashes_verified": len(levels),
          "direct_C_main_effect_checks": paired, "stationary_result_cells": len(stationary_results),
          "tv_result_cells": len(tv_results), "independent_cancellation_point": point}
(OUT / "coordinator-review.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps({"status": result["status"], "design_cells": len(design),
                  "matched_effect_checks": len(paired), "previous_manifests_unchanged": True}))
