"""ISO 532-1 Annex B compliance check of the released wheels (0.3.1 and 0.4.0).

Run once per wheel venv:
    <venv>/Scripts/python.exe -I compliance.py <repo-root> <label> <out.json>

1. Recomputes signals 2-25 with the installed `iso532` wheel and compares the
   bytes with the Astra 0.4.0 acceptance outputs (cross-check only).
2. Re-implements the per-point Annex B rule max(0.1, 0.05*|ref|) on every
   workbook reference point (stationary N and N'(z); time-varying N(t) and,
   for signals 6-13, the workbook's single N'(t) Bark curve).
3. Adds the workbook summary values Nmax and N5 (time-varying signals), with
   N5 computed both as the workbook PERCENTILE over its own row range and as
   the official CLI definition. Summary values are diagnostics: no tolerance
   for them is written in the workbook.
"""
import hashlib
import json
import pathlib
import re
import sys

import numpy as np
import openpyxl
import iso532
import importlib.metadata as md

ROOT = pathlib.Path(sys.argv[1]).resolve()
LABEL = sys.argv[2]
OUT = pathlib.Path(sys.argv[3])
OFFICIAL = ROOT / "tmp/c01-material/official"
INPUTS = ROOT / "tmp/acceptance-040-astra/contracts-inputs"
ASTRA = ROOT / ("tmp/acceptance-040-astra/contracts-output-"
                + ("candidate" if LABEL == "0.4.0" else "baseline"))
ASTRA_JSON = ROOT / "docs/verification/2026-11-04-release-0.4.0-fca4ccd/contracts/contracts-results.json"


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def tol(ref):
    return np.maximum(0.1, 0.05 * np.abs(ref))


def cli_n5(n):
    s = np.sort(np.asarray(n))
    j = int(0.95 * len(s))
    return float((s[j - 1] + s[j]) / 2)


astra = json.loads(ASTRA_JSON.read_text(encoding="utf-8"))
astra_key = "candidate" if LABEL == "0.4.0" else "baseline"
result = {"label": LABEL, "wheel_version": md.version("iso532"),
          "iso532_module": pathlib.Path(iso532.__file__).name,
          "inputs": {}, "cross_check": {}, "points": {}, "summary_values": {},
          "workbooks": {}}

# ---- outputs -------------------------------------------------------------
outputs = {}
for s in range(1, 26):
    p = INPUTS / f"sig{s}.bin"
    result["inputs"][s] = {"sha256": sha(p),
                           "matches_astra": sha(p) == astra["input_hashes"][str(s)]["decoded_sha256"]}
    x = np.fromfile(p, dtype="<f8")
    if s == 1:
        # third-octave level input: no Python entry point; reuse the Astra
        # Rust output after verifying its recorded hash
        o = {k: np.fromfile(ASTRA / f"sig1-{k}.bin", dtype="<f8") for k in ("n", "sp", "time")}
        ok = all(sha(ASTRA / f"sig1-{k}.bin") == astra["raw_output_sha256"][astra_key][f"sig1-{k}.bin"]
                 for k in ("n", "sp", "time"))
        result["cross_check"][s] = {"source": "astra-rust-output", "hash_verified": ok}
    elif s <= 5:
        n, sp, _ = iso532.loudness_zwst(x, 48000.0, "free")
        o = {"n": np.array([n]), "sp": np.asarray(sp), "time": np.array([0.0])}
    else:
        n, sp, _, t = iso532.loudness_zwtv(x, 48000.0, "diffuse" if s == 15 else "free")
        o = {"n": np.asarray(n), "sp": np.ascontiguousarray(sp).ravel(), "time": np.asarray(t)}
    if s > 1:
        cc = {}
        for k in ("n", "sp", "time"):
            ref = np.fromfile(ASTRA / f"sig{s}-{k}.bin", dtype="<f8")
            same = len(ref) == len(o[k]) and bool(np.all(ref.view("<u8") == o[k].astype("<f8").view("<u8")))
            cc[k] = same
        result["cross_check"][s] = {"source": "wheel", "bitwise_equal_to_astra": cc}
    outputs[s] = o

# ---- workbook references -------------------------------------------------
refs = {}
for wb_path in sorted(OFFICIAL.rglob("*.xlsx")):
    wv = openpyxl.load_workbook(wb_path, data_only=True, read_only=True)
    wf = openpyxl.load_workbook(wb_path, data_only=False, read_only=True)
    result["workbooks"][wb_path.name] = sha(wb_path)
    for sh in wv:
        s = int(re.search(r"\d+", sh.title).group())
        rows = list(sh.values)
        frows = list(wf[sh.title].values)
        if s <= 5:
            refs[s] = {"n": [float(rows[7][1])], "sp": [float(r[6]) for r in rows[7:247]]}
            continue
        data = [(i, r) for i, r in enumerate(rows) if i >= 10
                and isinstance(r[0], (int, float)) and isinstance(r[1], (int, float))]
        ref = {"time": [r[0] for _, r in data], "n": [r[1] for _, r in data],
               "excel_row": [i + 1 for i, _ in data]}
        if s <= 13:
            label = str(rows[8][11])
            ref["bark_index"] = round(float(re.search(r"[\d]+[.,]?[\d]*", label).group().replace(",", ".")) * 10) - 1
            ref["bark_label"] = label
            ref["sp"] = [r[11] for _, r in data]
        # summary rows: find "Nmax" / "N5" labels in column A of the top rows
        for i in range(0, 10):
            a = str(rows[i][0] or "")
            if a.startswith("Nmax"):
                ref["nmax_ref"] = float(rows[i][1])
                ref["nmax_cell"] = f"B{i + 1}"
            if a.startswith("N5"):
                ref["n5_ref"] = float(rows[i][1])
                ref["n5_formula"] = str(frows[i][1])
                ref["n5_cell"] = f"B{i + 1}"
        ref["note_A3"] = str(rows[2][0] or "")
        refs[s] = ref

# ---- per-point rule ------------------------------------------------------
tot_points = tot_fail = 0
global_min = (np.inf, None)
for s, ref in sorted(refs.items()):
    o = outputs[s]
    r = {}
    for field in ("n", "sp"):
        if field not in ref:
            continue
        want = np.asarray(ref[field], dtype=float)
        if s <= 5:
            got = o[field]
        else:
            idx = np.rint(np.asarray(ref["time"]) * 500).astype(int)
            assert np.max(np.abs(o["time"][idx] - np.asarray(ref["time"]))) < 1e-10
            got = o["n"] if field == "n" else o["sp"].reshape(240, -1)[ref["bark_index"]]
            got = got[idx]
        assert len(got) == len(want)
        margin = tol(want) - np.abs(got - want)
        i = int(np.argmin(margin))
        r[field] = {"points": int(len(want)), "failed": int(np.sum(margin < 0)),
                    "min_margin": float(margin[i]), "min_margin_index": i,
                    "got": float(got[i]), "ref": float(want[i])}
        tot_points += len(want)
        tot_fail += int(np.sum(margin < 0))
        if margin[i] < global_min[0]:
            global_min = (float(margin[i]), f"signal {s} {field} index {i}")
    result["points"][s] = r
result["points_total"] = {"points": tot_points, "failed": tot_fail,
                          "min_margin": global_min[0], "min_margin_at": global_min[1]}

# ---- Nmax / N5 diagnostics ----------------------------------------------
for s, ref in sorted(refs.items()):
    if s <= 5:
        continue
    n = outputs[s]["n"]
    d = {"nmax_ref": ref.get("nmax_ref"), "nmax_cell": ref.get("nmax_cell"),
         "nmax_got": float(np.max(n)), "n5_ref_cached": ref.get("n5_ref"),
         "n5_formula": ref.get("n5_formula"), "n5_cell": ref.get("n5_cell")}
    if d["nmax_ref"] is not None:
        d["nmax_diff"] = d["nmax_got"] - d["nmax_ref"]
        d["nmax_within_max_rule"] = bool(abs(d["nmax_diff"]) <= tol(d["nmax_ref"]))
    d["nmax_ref_equals_ref_column_max"] = bool(d["nmax_ref"] == max(ref["n"]))
    m = re.search(r"PERCENTILE\(([BE])(\d+):[BE](\d+),\s*0?\.95\)", d["n5_formula"] or "")
    if m:
        col, lo, hi = m.group(1), int(m.group(2)), int(m.group(3))
        # column E is the workbook's lower 5 % bound of N, not N itself
        # (signals 12/13); apply the same cell formula to both sides
        f = (lambda v: np.where(0.05 * v > 0.1, 0.95 * v, np.where(v < 0.1, 0.0, v - 0.1))) if col == "E" else (lambda v: v)
        d["n5_formula_column"] = col
        rows = [k for k, er in enumerate(ref["excel_row"]) if lo <= er <= hi]
        idx = np.rint(np.asarray(ref["time"])[rows] * 500).astype(int)
        idx = idx[idx < len(n)]
        d["n5_workbook_rows"] = [lo, hi]
        d["n5_workbook_rows_with_data"] = len(rows)
        d["n5_ref_recomputed"] = float(np.percentile(f(np.asarray(ref["n"])[rows]), 95))
        d["n5_got_workbook_def"] = float(np.percentile(f(n[idx]), 95))
        d["n5_diff_workbook_def"] = d["n5_got_workbook_def"] - d["n5_ref_cached"]
        d["n5_within_max_rule_workbook_def"] = bool(abs(d["n5_diff_workbook_def"]) <= tol(d["n5_ref_cached"]))
    d["n5_got_cli_def_full_output"] = cli_n5(n)
    if d["n5_ref_cached"] is not None:
        d["n5_diff_cli_def"] = d["n5_got_cli_def_full_output"] - d["n5_ref_cached"]
    result["summary_values"][s] = d

OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps({"label": LABEL, "points_total": result["points_total"],
                  "cross_check_all_equal": all(
                      v.get("hash_verified", True) and all(v.get("bitwise_equal_to_astra", {}).values())
                      for v in result["cross_check"].values()),
                  "inputs_match": all(v["matches_astra"] for v in result["inputs"].values())}, indent=1))
