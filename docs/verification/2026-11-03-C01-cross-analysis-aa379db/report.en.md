# C-01 tail-difference cross-analysis (Claude: independent reproduction of Astra's two rounds and closure of the residuals)

> Pair／對照: [繁體中文](report.md) · source: zh · synced 2026-11-03

- Date: 2026-11-03 (Asia/Taipei)
- Snapshot under test: `aa379db` (v0.3.1)
- Performed by: Claude (primary agent), not Astra
- Nature: cross-verification of [`2026-11-03-C01-zero-pad-aa379db/`](../2026-11-03-C01-zero-pad-aa379db/) and [`2026-11-03-C01-tail-root-cause-aa379db/`](../2026-11-03-C01-tail-root-cause-aa379db/); diagnostic only, no change to code, tests or goldens.
- Used by: [`docs/C01-F03-SLOPE-ALIGNMENT-DECISION-2026-11-03.md`](../../C01-F03-SLOPE-ALIGNMENT-DECISION-2026-11-03.md)

## 1. Question and conclusions

**Question.** After Astra's second round decomposed the Rust-vs-official-C difference at the four tail points (Annex B signals 18/23/24/25), two residuals stayed "unisolated": 1.2e-9 to 8.5e-9 in the slope stage after rounding removal, and ~1e-11 in the main stage. This round answers: (a) can Astra's numbers be reproduced independently; (b) what mechanism produces the two residuals; (c) how large are the differences over the whole signals; (d) are they inherited from MoSQITo.

**Conclusions.**

1. Astra's tail numbers reproduce: recomputing with an independently written temporal weighting over Astra's stage arrays matches Astra's 12 tail values: 7 bitwise, the rest within 6 ulp (≤2.2e-18, [`logs/repro_check.log`](logs/repro_check.log)); the Rust and C slope stages were ported to Python and validated bitwise (all 4340 frames of signal 18, 1703 sampled frames of signal 23, zero mismatches). Astra's verification is sound.
2. The slope residual is one algorithmic defect (F-05, "dropped last-cell remainder") plus the C program's own float32 constants. With the dropped remainder restored the Annex A way, the Rust port agrees with the C port (epsilon = 0, binary64 tables) to ≤1.4e-14 per frame and ≤2e-17 at the tails.
3. The main residual is the C float32 constants (`.0635f`, `0.4f`, `0.32f`, A0/DCB tables). A port with the same promotions matches the C core loudness to ≤4.4e-16 per frame.
4. All three deviations (per-frame rounding F-04, `USL[12][4]` F-03, F-05) are MoSQITo 1.2.1 behaviour inherited bitwise by Rust; MoSQITo's output on three sparse frames equals the Rust rounded value bitwise.
5. Over the whole signals the weighted output differs from C by at most 3.5e-3 sone, dominated by F-03; at the tails F-04 dominates.
6. The public `core::calc_slopes` wraps band 0 to band 20 when nm[20] > nm[0], yielding negative specific loudness; unreachable through the pipeline (main loudness fixes nm[20] = 0), recorded as API hardening item F-06.

## 2. Inputs and tools

All inputs are the material Astra's second round left in `tmp/c01-tail-root-cause-aa379db-run2/` (not in git); hashes in [`inputs.sha256.txt`](inputs.sha256.txt):

- Official `ISO_532-1.c` (SHA-256 `a74b45ed…834491`, matching Astra's record) and Astra's stage wrapper `stages.c`/`stages.dll` (`rc_slopes`, `rc_public`).
- Astra's Rust probe `c01-root-probe.exe` (mode `public`, unmodified crate snapshot).
- Per-signal stage arrays: `R-pipeline/{tol,core,nl,slope_raw,slope_raw22,slope_round}.bin`, `C-core-on-Rtol.bin`, `C-slope-on-Rnl-total.bin`.
- MoSQITo 1.2.1 (`.venv`) `_calc_slopes`.
- The scripts in this folder run with `C01_WORK` pointing at that directory; outputs in [`logs/`](logs/). Python 3.11.9, NumPy 2.4.6.

## 3. Method and results

### 3.1 Bitwise ports (`slope_trace.py`)

- `c_slopes`: Python port of the official `f_calc_slopes` (lines 839–937), tables promoted from float32, `_ZUP += 0.0001f`.
- `rust_slopes`: port of `calc_slopes_impl` without the rounding at lines 161–165, including `r8`, both `get_rns_index` comparisons and the band-0 wrap.
- Validation ([`logs/slope_trace.log`](logs/slope_trace.log)): C port vs `C-slope-on-Rnl-total.bin`, Rust port (0.24 and 0.22 tables) vs `slope_raw.bin`/`slope_raw22.bin`; all 4340 frames of signal 18 and every third frame of signal 23 (1703): zero mismatches.

### 3.2 Two components of the slope residual (`dense_check.py`)

Frame counts of `raw22 − C variant` over the first 4333 frames of signal 18 ([`logs/dense_check.log`](logs/dense_check.log)):

| C variant | >1e-12 | >1e-10 | >1e-6 | >1e-4 |
|---|---|---|---|---|
| original (epsilon, float32 tables) | 3382 | 3244 | 887 | 38 |
| epsilon = 0 | 3382 | 3243 | 40 | 38 |
| epsilon = 0 and binary64 tables | 40 | 40 | 40 | 38 |

With the C program's own promotions removed, only 40 "sparse" frames remain (63/38/31 for signals 23/24/25); the other 2949 frames differ by ≤1e-13. The dense small differences are the C float32 constants; the sparse large ones have a different mechanism.

### 3.3 Mechanism of the sparse frames = F-05 (`slope_trace.py trace`, `sliver_check.py`)

Signal 23 frame 3893 ([`logs/slope_trace.log`](logs/slope_trace.log)): in band 3 a slope segment starts at the last grid cell (j = 34) and reaches the core loudness 0.0995 at Z = 3.438; C then adds the flat remainder up to ZUP 3.5. The Rust grid loop has no further cell to process, so the remainder 3.438 → 3.5 is never integrated and band 4 starts at 3.438 (back-fill); net +1.38e-2 sone. Frames 4017 and 3981 are the same pattern (bands 19/18).

`rust_slopes_fixed` completes the band after the grid loop as Annex A does ([`logs/sliver_check.log`](logs/sliver_check.log)):

| Signal | Sparse frames | Restoration triggered | False triggers | Per-frame max \|Rust−C(eps0,f64)\| after fix | Tail fixed−C(eps0,f64) | Tail fixed−official C |
|---|---|---|---|---|---|---|
| 18 | 40 | 40 | 0 | 1.42e-14 | −5.2e-18 | −3.46e-11 |
| 23 | 63 | 63 | 0 | 1.07e-14 | −1.8e-17 | +6.06e-11 |
| 24 | 38 | 38 | 0 | 8.88e-15 | −1.1e-17 | −5.44e-11 |
| 25 | 31 | 31 | 1 (benign, ≤1e-13) | 8.88e-15 | −6.3e-18 | −3.47e-11 |

The 3–6e-11 against the official C equals the C(eps0,f64)-vs-official difference exactly, i.e. the C float32 constants.

### 3.4 Closure also holds with 0.24 (`sliver_check_024.py`)

With 0.24 on both sides ([`logs/sliver_check_024.log`](logs/sliver_check_024.log)): per frame ≤1.42e-14; tails vs C with official arithmetic and only the cell changed to 0.24f: −3.46e-11/+6.05e-11/−5.44e-11/−3.47e-11; vs the unmodified C (0.22): −1.43e-8/−1.28e-7/−9.30e-9/−3.47e-11; whole-series weighted max 2.97e-3/1.53e-3/3.53e-3/5.56e-7 sone. The F-04/F-05 fixes are independent of the coefficient choice.

### 3.5 Main residual (`main_check.py`)

[`logs/main_check.log`](logs/main_check.log): the binary64 port equals the Rust core loudness bitwise (0 mismatches); the C-style port (`.0635f`, `0.4f`/`0.32f`, A0/DCB float32) matches the C core loudness to ≤4.4e-16 (127/166/145/131 one-ulp frames). Individually, A0/DCB float32 contributes 6.5e-8 per frame and `.0635f` 8e-9. The main residual is entirely the C float32 constants.

### 3.6 Band-0 wrap (`ctypes_check.py`, `band0_real-main.rs.txt`, `e2e_band0.py`)

[`logs/e2e_band0_ctypes.log`](logs/e2e_band0_ctypes.log), [`logs/band0_real.log`](logs/band0_real.log): on a synthetic frame with nm[0] = 0, nm[20] = 1 the official C gives total 0.400 while the real Rust crate gives 0.982 with spec[0] = −9.8575. But no frame of the four NL histories has nm[20] > 0 (`band0scan`), and end to end (12.5 kHz tone, >8 kHz noise, white noise, 1 kHz tone) Rust differs from C by ≤1.8e-3 sone with minimum specific loudness 0 on both sides. The wrap is reachable only by calling the public `calc_slopes` directly.

Note: `band0_real.log` was produced by the scratch project, whose `main.rs` has one extra duplicate case line (`only nm20=1.0 spec check`) relative to the copy filed here; its values equal the third case.

### 3.7 MoSQITo inheritance

Same log: MoSQITo `_calc_slopes` on signal 23 frames 3893/4017/3981 equals the Rust rounded totals bitwise (4.765/13.309/7.649); the official C gives 4.7516/13.3136/7.6544.

## 4. Judgement of Astra's verification

- Preregistered design, bitwise baseline/replay controls, ordered substitution and the reverse control are appropriate; the tail numbers reproduce independently (`repro_check.py`: baseline, remove_R_rounding, replace_slopes_C × four signals, worst 2.2e-18).
- The "rounding removal alone does not reach 1e-14" gate is correct; the residual is attributed in this round. It is not a methodological flaw, the experiment simply stopped at stage granularity.
- Astra did not name F-05 as a defect because its sparse frames contribute only ~1e-9 at the tails; the per-frame comparison in this round exposes the 1e-2 sone single-frame differences.

## 5. Delivery inventory

| File | Content |
|---|---|
| `report.md` / `report.en.md` | this report |
| `repro_check.py` | reproduces Astra's 12 tail values with an independent TW |
| `slope_trace.py` | bitwise ports, validation, tracing, band-0 tests |
| `dense_check.py` | C variants separating dense from sparse differences |
| `sliver_check.py` / `sliver_check_024.py` | F-05 restoration and closure (0.22 / 0.24) |
| `main_check.py` | main-stage float32 closure |
| `e2e_band0.py`, `ctypes_check.py`, `band0_real-*.txt` | band-0 end-to-end and direct calls |
| `logs/*.log` | outputs of this re-run |
| `inputs.sha256.txt` | hashes of the external inputs |
| `delivery-check.md`, `delivery-integrity.json` | redaction and integrity |
