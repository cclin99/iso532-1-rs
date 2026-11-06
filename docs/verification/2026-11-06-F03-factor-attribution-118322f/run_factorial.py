"""Full factorial over the slope-stage factors (F1 USL[12][4], F2 ZUP band-edge constant, F3 binary32
literals) for every Rust stage dump (F4 pressure conversion x F6 nonlinear-decay init), plus the
negative control USL[12][4] = 0.30. Writes out/fact/<cell>-sig<s>-n.npy (N(t) on the 2 ms output grid),
-spb.npy (specific loudness at the workbook's designated Bark, signals 6-13), -grid.npy (number of
0.1-Bark samples written per output frame; 240 = intact grid). Stationary: -n.npy (1), -sp.npy (240).
Usage: run_factorial.py <procs>"""
import sys, pathlib, json, time, numpy as np
from multiprocessing import Pool
from slopes_port import Slopes, tv_pipeline
import refs

HERE = pathlib.Path(__file__).resolve().parent
R = HERE / "out/rust"
F = HERE / "out/fact"
F.mkdir(parents=True, exist_ok=True)
SCALES = ("s22", "cal")
INITS = ("zero", "tail")
CELLS = [(u, e, f) for u in (0.24, 0.22) for e in (0.0, 1e-4) for f in (False, True)]
NEG = (0.30, 1e-4, False)


def cell_name(scale, init, u, e, f):
    return f"{scale}-{init}-u{u:.2f}-e{'1e-4' if e else '0'}-f{int(f)}"


def tv_task(args):
    s, scale, init, bark_index = args
    nl = np.fromfile(R / f"{scale}-sig{s}-{init}-nl.bin", "<f8")
    nl = nl.reshape(21, len(nl) // 21)
    cells = list(CELLS) + ([NEG] if (scale, init) == ("s22", "zero") else [])
    t0 = time.time()
    for u, e, f in cells:
        sl = Slopes(u, e, f)
        n_time = nl.shape[1]
        loud = np.empty(n_time)
        n_out = -(-n_time // 4)
        spb = np.full(n_out, np.nan)
        grid = np.zeros(n_out, dtype=np.int16)
        for t in range(n_time):
            ws = t % 4 == 0
            total, sp, k = sl.frame(nl[:, t], ws)
            loud[t] = total
            if ws:
                grid[t // 4] = k
                if bark_index is not None:
                    spb[t // 4] = sp[bark_index]
        from slopes_port import temporal_weighting
        n = temporal_weighting(loud)[::4]
        name = cell_name(scale, init, u, e, f)
        np.save(F / f"{name}-sig{s}-n.npy", n)
        np.save(F / f"{name}-sig{s}-grid.npy", grid)
        if bark_index is not None:
            np.save(F / f"{name}-sig{s}-spb.npy", spb)
    return s, scale, init, round(time.time() - t0, 1)


def stationary():
    out = {}
    nm1 = np.fromfile(R / "s22-sig1-nm.bin", "<f8")
    for u, e, f in CELLS + [NEG]:
        n, sp, k = Slopes(u, e, f).frame(nm1, True)
        name = cell_name("levels", "na", u, e, f)
        np.save(F / f"{name}-sig1-n.npy", np.array([n])); np.save(F / f"{name}-sig1-sp.npy", np.array(sp))
        out[f"{name}-sig1"] = {"N": n, "grid": k}
    for s in range(2, 6):
        for scale in SCALES:
            nm = np.fromfile(R / f"{scale}-sig{s}-nm.bin", "<f8")
            for u, e, f in CELLS + ([NEG] if scale == "s22" else []):
                n, sp, k = Slopes(u, e, f).frame(nm, True)
                name = cell_name(scale, "zwst", u, e, f)
                np.save(F / f"{name}-sig{s}-n.npy", np.array([n])); np.save(F / f"{name}-sig{s}-sp.npy", np.array(sp))
                out[f"{name}-sig{s}"] = {"N": n, "grid": k}
    return out


if __name__ == "__main__":
    procs = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    rf = refs.load_refs()
    t0 = time.time()
    st = stationary()
    print(f"stationary done {time.time() - t0:.1f}s", flush=True)
    tasks = [(s, sc, ini, rf[s].get("bark_index")) for s in range(6, 26) for sc in SCALES for ini in INITS]
    tasks.sort(key=lambda a: -rf[a[0]]["N"].size)  # long signals first
    with Pool(procs) as p:
        for r in p.imap_unordered(tv_task, tasks):
            print("done", r, flush=True)
    json.dump({"stationary": st, "cells": [cell_name("<scale>", "<init>", u, e, f) for u, e, f in CELLS + [NEG]],
               "elapsed_s": round(time.time() - t0, 1)}, open(F / "run-index.json", "w"), indent=1)
    print("all done", round(time.time() - t0, 1), "s")
