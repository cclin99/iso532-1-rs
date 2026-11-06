"""Factor attribution analysis. Reads: out/fact (port factorial), out/rust (iso532 stage dumps),
out/sqat (SQAT with the ZUP constant removed, Octave), the 2026-11-05 outputs (SQAT 0.22/0.24/0.30 with
the constant, MoSQITo 0.22/0.24, official C CLI 0.22/0.24) and the Annex B workbooks.
Usage: analyze.py <results.json>"""
import sys, json, pathlib, hashlib, subprocess, numpy as np
import refs
from run_factorial import CELLS, NEG, cell_name, SCALES, INITS

HERE = pathlib.Path(__file__).resolve().parent
F, R, Q = HERE / "out/fact", HERE / "out/rust", HERE / "out/sqat"
OLD = refs.ROOT / "tmp/impl-2026-11-05/out"
TV = range(6, 26)
EQ4 = 5e-5 + 1e-9


def at_ref(n, ref):
    return n[np.rint(ref["t"] * 500).astype(int)]


def c_at_ref(variant, s, ref):
    o = refs.c_cli(variant, s)
    j = np.searchsorted(np.round(o["t"], 4), np.round(ref["t"], 4))
    assert np.allclose(o["t"][j], ref["t"])
    return o["N"][j]


def old_n(variant, s):
    if variant.startswith("mosqito"):
        return np.load(OLD / f"{variant}-sig{s}-n.npy").ravel()
    return np.fromfile(OLD / f"{variant}-sig{s}-n.bin", "<f8")


def stats(d):
    d = np.asarray(d, float)
    return {"max_abs": float(np.max(np.abs(d))), "median_abs": float(np.median(np.abs(d))),
            "mean_signed": float(np.mean(d)), "n": int(d.size), "within_5e-5": int(np.sum(np.abs(d) <= EQ4))}


def tv_metrics(n_by_sig, rf, c22, c24, decisive):
    """n_by_sig: {s: N at workbook times}. Returns workbook / decisive / vs-C stats over signals 6-25."""
    dw, dd, dc22, dc24, outside, per = [], [], [], [], 0, {}
    for s in TV:
        ref = rf[s]; n = n_by_sig[s]
        d = n - ref["N"]; dw.append(d); outside += int(np.sum(np.abs(d) > refs.tol(ref["N"])))
        dd.append(d[decisive[s]]); dc22.append(n - c22[s]); dc24.append(n - c24[s])
        per[s] = {"max_abs": float(np.max(np.abs(d))), "median_abs": float(np.median(np.abs(d))), "mean_signed": float(np.mean(d)),
                  "within_5e-5": int(np.sum(np.abs(d) <= EQ4)), "n": int(d.size),
                  "Nmax_err": float(np.max(n) - ref["nmax"]), "N5_err": float(refs.n5_workbook(n, ref) - ref["n5"])}
    return {"workbook": stats(np.concatenate(dw)) | {"outside_tolerance": outside},
            "decisive": stats(np.concatenate(dd)), "vs_c022": stats(np.concatenate(dc22)), "vs_c024": stats(np.concatenate(dc24)),
            "per_signal": per}


def load_cell(scale, init, u, e, f, rf):
    name = cell_name(scale, init, u, e, f)
    out = {}
    for s in TV:
        p = F / f"{name}-sig{s}-n.npy"
        if not p.exists():
            return None
        out[s] = at_ref(np.load(p), rf[s])
    return out


def main():
    rf = refs.load_refs()
    res = {"frozen": frozen(), "calibration": json.load(open(HERE / "calibration.json")),
           "input_hashes": json.load(open(refs.ROOT / "tmp/impl-2026-11-05/in/inputs.json"))}
    c22 = {s: c_at_ref("022", s, rf[s]) for s in TV}
    c24 = {s: c_at_ref("024", s, rf[s]) for s in TV}
    decisive = {s: np.abs(c24[s] - c22[s]) >= 2e-4 - 1e-9 for s in TV}
    res["decisive_points"] = int(sum(int(m.sum()) for m in decisive.values()))

    # ---- reference implementations at the workbook points (2026-11-05 outputs + new SQAT runs)
    impls = {"official_c_0.22": c22, "official_c_0.24": c24}
    for v in ("sqat_0.24", "sqat_0.22", "sqat_0.30", "mosqito_0.24", "mosqito_0.22", "rust_0.24", "rust_0.22"):
        impls[v] = {s: at_ref(old_n(v, s), rf[s]) for s in TV}
    for v in ("sqat_e0_0.24", "sqat_e0_0.22"):
        if all((Q / f"{v}-sig{s}-n.bin").exists() for s in TV):
            impls[v] = {s: at_ref(np.fromfile(Q / f"{v}-sig{s}-n.bin", "<f8"), rf[s]) for s in TV}
        else:
            res.setdefault("pending", []).append(v)
    res["implementations"] = {k: tv_metrics(v, rf, c22, c24, decisive) for k, v in impls.items()}

    # ---- factorial cells
    cells = {}
    for scale in SCALES:
        for init in INITS:
            for u, e, f in CELLS + ([NEG] if (scale, init) == ("s22", "zero") else []):
                c = load_cell(scale, init, u, e, f, rf)
                if c is None:
                    res.setdefault("pending", []).append(cell_name(scale, init, u, e, f)); continue
                cells[cell_name(scale, init, u, e, f)] = c
    res["cells"] = {k: tv_metrics(v, rf, c22, c24, decisive) for k, v in cells.items()}
    res["cells_pending"] = len(res.get("pending", []))

    # ---- grid diagnostics (number of 0.1 Bark samples per frame; 240 = intact)
    grid = {}
    for name in cells:
        bad = tot = 0
        for s in TV:
            g = np.load(F / f"{name}-sig{s}-grid.npy"); bad += int(np.sum(g != 240)); tot += g.size
        grid[name] = {"frames_not_240": bad, "frames": tot}
    res["grid_samples"] = grid

    # ---- specific loudness at the designated Bark (signals 6-13), cells with intact grid only
    spb = {}
    for name in cells:
        if grid[name]["frames_not_240"]:
            continue
        d = []
        for s in range(6, 14):
            v = np.load(F / f"{name}-sig{s}-spb.npy"); d.append(at_ref(v, rf[s]) - rf[s]["Nspec_t"])
        spb[name] = stats(np.concatenate(d))
    res["spec_designated_bark"] = spb

    # ---- main effects: paired differences over the other factors (all workbook points, 6-25)
    def pair_effect(name_a, name_b):
        a, b = cells.get(name_a), cells.get(name_b)
        if a is None or b is None:
            return None
        d = np.concatenate([a[s] - b[s] for s in TV])
        return {"max_abs": float(np.max(np.abs(d))), "moved_ge_1e-9": int(np.sum(np.abs(d) >= 1e-9)), "mean_signed": float(np.mean(d)), "n": int(d.size)}
    effects = {"F1_usl_0.22_minus_0.24": [], "F2_eps_1e-4_minus_0": [], "F3_f32_on_minus_off": [], "F4_cal_minus_2sqrt2": [], "F6_tail_minus_zero": []}
    for scale in SCALES:
        for init in INITS:
            for u, e, f in CELLS:
                base = cell_name(scale, init, u, e, f)
                if u == 0.24:
                    effects["F1_usl_0.22_minus_0.24"].append((base, pair_effect(cell_name(scale, init, 0.22, e, f), base)))
                if e == 0.0:
                    effects["F2_eps_1e-4_minus_0"].append((base, pair_effect(cell_name(scale, init, u, 1e-4, f), base)))
                if not f:
                    effects["F3_f32_on_minus_off"].append((base, pair_effect(cell_name(scale, init, u, e, True), base)))
                if scale == "s22":
                    effects["F4_cal_minus_2sqrt2"].append((base, pair_effect(cell_name("cal", init, u, e, f), base)))
                if init == "zero":
                    effects["F6_tail_minus_zero"].append((base, pair_effect(cell_name(scale, "tail", u, e, f), base)))
    res["main_effects"] = {k: {"pairs": [{"base": b, **(p or {"pending": True})} for b, p in v],
                               "max_abs_over_pairs": max((p["max_abs"] for _, p in v if p), default=None),
                               "min_abs_over_pairs": min((p["max_abs"] for _, p in v if p), default=None)} for k, v in effects.items()}
    # F6 localisation: last workbook time at which tail != zero (per signal, F1=0.22, F2=1e-4, f32 off, s22)
    loc = {}
    a, b = cells.get(cell_name("s22", "tail", 0.22, 1e-4, False)), cells.get(cell_name("s22", "zero", 0.22, 1e-4, False))
    if a and b:
        for s in TV:
            m = np.abs(a[s] - b[s]) >= 1e-9
            loc[s] = {"points_moved": int(m.sum()), "last_time_s": float(rf[s]["t"][m].max()) if m.any() else None,
                      "max_abs": float(np.max(np.abs(a[s] - b[s]))), "moved_at_decisive": int(np.sum(m & decisive[s]))}
    res["F6_localisation"] = loc
    # F2 effect vs band-0 core loudness (H2 mechanism): per signal, mean(F2 effect) and mean nm0 at workbook points
    mech = {}
    for s in TV:
        a = cells.get(cell_name("s22", "zero", 0.22, 1e-4, False)); b = cells.get(cell_name("s22", "zero", 0.22, 0.0, False))
        if not (a and b):
            break
        nl = np.fromfile(R / f"s22-sig{s}-zero-nl.bin", "<f8"); nl = nl.reshape(21, len(nl) // 21)
        nm0 = nl[0, ::4]; nm0 = at_ref(nm0, rf[s])
        d = a[s] - b[s]
        mech[s] = {"mean_F2_effect": float(d.mean()), "mean_1e-4_x_nm0": float(1e-4 * nm0.mean()), "max_F2_effect": float(np.max(np.abs(d))),
                   "corr_effect_vs_nm0": float(np.corrcoef(d, nm0)[0, 1]) if np.std(nm0) > 0 and np.std(d) > 0 else None}
    res["F2_mechanism"] = mech

    # ---- validation of the port and cross-implementation identities (full 2 ms grid, not only workbook points)
    val = {}
    for s in TV:
        rn = np.fromfile(R / f"s22-sig{s}-zero-n.bin", "<f8")
        pn = np.load(F / f"{cell_name('s22', 'zero', 0.24, 0.0, False)}-sig{s}-n.npy")
        pe = np.load(F / f"{cell_name('s22', 'zero', 0.24, 1e-4, False)}-sig{s}-n.npy")
        p22 = np.load(F / f"{cell_name('s22', 'zero', 0.22, 1e-4, False)}-sig{s}-n.npy")
        q24 = old_n("sqat_0.24", s); q22 = old_n("sqat_0.22", s); L = min(len(rn), len(q24))
        v = {"port_eps0_vs_iso532": float(np.max(np.abs(pn - rn))), "port_eps_vs_sqat_0.24": float(np.max(np.abs(pe[:L] - q24[:L]))),
             "port_0.22_eps_vs_sqat_0.22": float(np.max(np.abs(p22[:L] - q22[:L]))), "len_iso532": len(rn), "len_sqat": len(q24)}
        if (Q / f"sqat_e0_0.24-sig{s}-n.bin").exists():
            qe = np.fromfile(Q / f"sqat_e0_0.24-sig{s}-n.bin", "<f8"); v["sqat_eps0_0.24_vs_iso532_shipped"] = float(np.max(np.abs(qe[:L] - rn[:L])))
        if (Q / f"sqat_e0_0.22-sig{s}-n.bin").exists():
            qe = np.fromfile(Q / f"sqat_e0_0.22-sig{s}-n.bin", "<f8"); p = np.load(F / f"{cell_name('s22', 'zero', 0.22, 0.0, False)}-sig{s}-n.npy")
            v["sqat_eps0_0.22_vs_port_0.22_eps0"] = float(np.max(np.abs(qe[:L] - p[:L])))
        val[s] = v
    res["validation"] = val
    res["validation_summary"] = {k: max(v[k] for v in val.values() if k in v) for k in
                                 ("port_eps0_vs_iso532", "port_eps_vs_sqat_0.24", "port_0.22_eps_vs_sqat_0.22", "sqat_eps0_0.24_vs_iso532_shipped", "sqat_eps0_0.22_vs_port_0.22_eps0")
                                 if any(k in v for v in val.values())}

    # ---- stationary: signal 1 (levels) and 2-5 (front ends)
    st = {"signal_1": {}, "signals_2_5": {}}
    for u, e, f in CELLS + [NEG]:
        name = cell_name("levels", "na", u, e, f)
        n = float(np.load(F / f"{name}-sig1-n.npy")[0]); sp = np.load(F / f"{name}-sig1-sp.npy")
        st["signal_1"][name] = {"N": n, "N_err": n - rf[1]["N"], "Nspec_max_abs_err": float(np.max(np.abs(sp - rf[1]["Nspec"]))),
                                "Nspec_within_5e-5": int(np.sum(np.abs(sp - rf[1]["Nspec"]) <= EQ4))}
    for v in ("sqat_0.24", "sqat_0.22", "rust_0.24", "rust_0.22", "mosqito_0.24", "mosqito_0.22"):
        n = float(old_n(v, 1)[0]); st["signal_1"][v] = {"N": n, "N_err": n - rf[1]["N"]}
    st["signal_1"]["official_c_0.22"] = {"N": float(refs.c_cli("022", 1)["N"][0]), "N_err": float(refs.c_cli("022", 1)["N"][0] - rf[1]["N"])}
    st["signal_1"]["workbook"] = rf[1]["N"]
    for s in range(2, 6):
        row = {"workbook_N": rf[s]["N"], "official_c_0.22": float(refs.c_cli("022", s)["N"][0] - rf[s]["N"])}
        for scale in SCALES:
            for u, e, f in CELLS:
                name = cell_name(scale, "zwst", u, e, f); n = float(np.load(F / f"{name}-sig{s}-n.npy")[0]); row[name] = n - rf[s]["N"]
        for v in ("sqat_0.24", "sqat_0.22", "sqat_0.24-skip0", "sqat_0.22-skip0", "mosqito_0.24", "mosqito_0.22", "rust_0.24", "rust_0.22"):
            try:
                row[v] = float(old_n(v, s)[0] - rf[s]["N"])
            except FileNotFoundError:
                pass
        for v in ("sqat_e0_0.24", "sqat_e0_0.22", "sqat_e0_0.24-skip0", "sqat_e0_0.22-skip0"):
            p = Q / f"{v}-sig{s}-n.bin"
            if p.exists():
                row[v] = float(np.fromfile(p, "<f8")[0] - rf[s]["N"])
        row_pct = {k: (v / rf[s]["N"] * 100 if k != "workbook_N" else v) for k, v in row.items()}
        st["signals_2_5"][s] = {"err_sone": row, "err_pct": row_pct}
    res["stationary"] = st
    res["signal_names"] = refs.SIGNAL_NAMES
    json.dump(res, open(sys.argv[1], "w"), indent=1, default=float)
    print("written", sys.argv[1], "pending:", res.get("pending"))


def frozen():
    def run(cmd):
        return subprocess.run(cmd, capture_output=True, text=True, shell=True).stdout.strip()
    return {"repo_head": run("git -C <REPO> rev-parse HEAD"), "crate_diff_vs_118322f": run("git -C <REPO> diff 118322f HEAD --stat -- iso532/") or "(empty: identical)",
            "rustc": run("rustc --version"), "cargo": run("cargo --version"), "python": sys.version.split()[0], "numpy": np.__version__,
            "octave": "GNU Octave 11.3.0 (x86_64-w64-mingw32)", "sqat": "v2.0, GitHub ggrecow/SQAT tag v2.0 (94f489c053d1366da05d5e62838c3f54ac7715c3), Loudness_ISO532_1.m",
            "official_c_cli": "2026-11-05 round, MSVC x64 /O2 /fp:precise, v022 unmodified / v024 one cell (tmp/usl-2026-11-05)",
            "mosqito": "1.2.1 (2026-11-05 run, run_mosqito.py)", "sha256_slopes_port": hashlib.sha256((HERE / "slopes_port.py").read_bytes()).hexdigest(),
            "sha256_harness_main_rs": hashlib.sha256((HERE / "harness/src/main.rs").read_bytes()).hexdigest()}


if __name__ == "__main__":
    main()
