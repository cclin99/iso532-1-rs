"""Annex B workbook references (same loader as the 2026-11-05 analysis) and the official C CLI outputs
(2026-11-05 round, `tmp/usl-2026-11-05/cli-v0{22,24}`; 2*sqrt(2) float WAVs, 4-decimal output)."""
import re, pathlib, numpy as np, openpyxl

ROOT = pathlib.Path("<REPO>")
OFF = ROOT / "tmp/c01-material/official"
CLI = ROOT / "tmp/usl-2026-11-05"
SIGNAL_NAMES = {}


def load_refs():
    refs = {}
    for wb in sorted(OFF.rglob("*.xlsx")):
        w = openpyxl.load_workbook(wb, data_only=True, read_only=True)
        wf = openpyxl.load_workbook(wb, data_only=False, read_only=True)
        for sh in w:
            s = int(re.search(r"\d+", sh.title).group()); rows = list(sh.values); frows = list(wf[sh.title].values)
            if s <= 5:
                refs[s] = {"N": float(rows[7][1]), "Nspec": np.array([float(r[6]) for r in rows[7:247]])}
                continue
            data = [(i, r) for i, r in enumerate(rows) if i >= 10 and isinstance(r[0], (int, float)) and isinstance(r[1], (int, float))]
            ref = {"t": np.array([r[0] for _, r in data]), "N": np.array([r[1] for _, r in data], float),
                   "row": np.array([i + 1 for i, _ in data]), "nmax": float(rows[4][1]), "n5": float(rows[5][1]),
                   "n5_formula": str(frows[5][1])}
            if s <= 13:
                label = str(rows[8][11])
                ref["bark_index"] = round(float(re.search(r"[\d]+[.,]?[\d]*", label).group().replace(",", ".")) * 10) - 1
                ref["Nspec_t"] = np.array([r[11] for _, r in data], float)
            refs[s] = ref
    for p in OFF.rglob("Test signal *.wav"):
        m = re.match(r"Test signal (\d+) \((.*)\)\.wav", p.name)
        SIGNAL_NAMES[int(m.group(1))] = m.group(2)
    SIGNAL_NAMES[1] = "28 third-octave levels"
    return refs


def c_cli(variant, s):
    """variant '022' or '024'. Stationary: {'N', 'Nspec'}; time varying: {'t', 'N', 'spec_t', 'spec'}."""
    d = CLI / f"cli-v{variant}/sig{s}"
    lt = (d / "Loudness.csv").read_text()
    if s <= 5:
        n = float(re.search(r"N / sone \((?:free|diffuse) field\);\s*([\d.]+)", lt).group(1))
        sp = np.array([[float(x) for x in l.split(";") if x.strip()] for l in (d / "SpecLoudness.csv").read_text().splitlines() if re.match(r"^\d", l)]).ravel()[-240:]
        return {"N": np.array([n]), "Nspec": sp}
    rows = [l.split(";") for l in lt.splitlines() if re.match(r"^\d", l)]
    t = np.array([float(a) for a, _ in rows]); n = np.array([float(b) for _, b in rows])
    sp_rows = [[float(x) for x in l.split(";") if x.strip()] for l in (d / "SpecLoudness.csv").read_text().splitlines() if re.match(r"^\d", l)]
    sp = np.array(sp_rows)
    return {"t": t, "N": n, "spec_t": sp[:, 0], "spec": sp[:, 1:241]}


def n5_workbook(nvals, ref):
    m = re.search(r"PERCENTILE\(([BE])(\d+):[BE](\d+)", ref["n5_formula"])
    col, lo, hi = m.group(1), int(m.group(2)), int(m.group(3))
    sel = (ref["row"] >= lo) & (ref["row"] <= hi)
    f = (lambda v: np.where(0.05 * v > 0.1, 0.95 * v, np.where(v < 0.1, 0.0, v - 0.1))) if col == "E" else (lambda v: v)
    return float(np.percentile(f(nvals[sel]), 95))


def tol(r):
    return np.maximum(0.1, 0.05 * np.abs(r))
