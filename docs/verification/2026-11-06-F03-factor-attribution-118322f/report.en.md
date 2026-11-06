# Factor attribution of the Annex B errors: MoSQITo 1.2.1, iso532 0.4.0, SQAT v2.0 and the official C program

> 對照／Pair: [繁體中文](report.md) · source: zh · synced 2026-11-06

Main agent (Claude Fable 5.1), 2026-11-06 (Asia/Taipei). Snapshot under test: `62e8559` (the `iso532` crate is byte-identical to `v0.4.0` = `118322f`). Independent of Astra's parallel factorial round, whose folder was not read. Preregistration: `preregistration.md`; replay: `replay.md`; every number comes from `results.json` (produced by `analyze.py`).

## 1. Answers

1. **Two constants separate iso532 0.4.0 from the official C program on the time-varying path, and nothing else at the workbook's resolution.** F1, `USL[12][4]` (0.24 vs 0.22), moves N(t) by up to 0.0169 sone. F2, the band-edge constant `_ZUP += .0001f` (C line 862, mirrored by SQAT line 528, absent from MoSQITo and iso532), moves N(t) by up to 1.8e-4 sone and is the whole residual that survived F1 (iso532 0.22: max 2.19e-4 at signals 9/14/15). With both switched, iso532's own nonlinear-decay output reproduces the workbook exactly as well as SQAT 0.22 does: max 7.9e-5, 45,487 of 48,711 points within 5e-5, 11,224 of the 12,287 decisive points within 5e-5 (identical counts to SQAT 0.22), and matches SQAT 0.22 itself to ≤ 1.9e-12 (≤ 6.5e-8 on signals 11–13, see §6).
2. **SQAT v2.0 differs from the official program by F1 only** (H1): shipped 0.24 → 0.0169 max; one cell → rounding level.
3. **MoSQITo 1.2.1 differs by F1 + F2 + its own slope/temporal deviations F-04…F-07 (F7)**: with the cell set to 0.22 the maximum error is still 0.0233 sone; F7 is not toggleable here and is measured as the whole of that residual, since F6 (nonlinear-decay initial state) is inert on Annex B (§4.5).
4. **The stationary errors of iso532 `zwst` and MoSQITo (+0.23 %, +0.82 %, +0.42 %, −0.77 % on signals 2–5) are untouched by F1, F2 and F3**: they are the front end (MoSQITo Butterworth/FFT third-octave spectrum), confirming the 2026-11-05 ZWST root-cause round. SQAT's Annex A front end with 0.2 s skip is within 0.0013 %; without the skip within 0.094 %.
5. **F3 (binary32 literals of the C program) changes N by ≤ 9.0e-7 sone** and is irrelevant at the 4-decimal level. **F4 (calibration-file conversion, +0.0226 dB)** raises N by ≈ +0.15 % (0.070 sone max) and destroys the 4-decimal agreement (2,920 points instead of 45,487), so the workbooks are 2√2-converted, as the provenance round found.
6. **The mechanism of F2** is confirmed numerically: the C program integrates band 0 over 0.9001 Bark instead of 0.9 (the later bands telescope), so N gains 1e-4 × core loudness of band 0; the mean F2 effect per signal equals the mean of 1e-4 × nm[0] to three significant digits on every affected signal (e.g. 14: 8.0e-5 / 8.0e-5; 15: 1.164e-4 / 1.164e-4), correlation 0.91–0.99, and signals without low-frequency energy (6–8, 10–13, 20–23, 25) show exactly zero effect. Slope segments clamped at the shifted band edge add the remaining ≤ USL × 1e-4 on specific loudness.
7. Hence the user's observation that 0.24 is not a single-factor explanation is correct in this precise sense: F1 is the only factor that reaches the 2e-4 decisive-point threshold, but the residual of the MoSQITo lineage after F1 is a second, independent, additive constant (F2), not noise, not the front end, not the initial state.

## 2. Scope and freeze

- iso532 at `62e8559` (`git diff 118322f HEAD -- iso532/` empty), built from the main tree by the harness in release mode; rustc/cargo versions in `results.json["frozen"]`.
- Official C CLI outputs: the two MSVC x64 `/O2 /fp:precise` builds of the 2026-11-05 round (v022 unmodified = 0.22f, v024 one cell), 2√2 float WAVs, 4-decimal CSV output.
- SQAT v2.0 (`ggrecow/SQAT` tag `v2.0` = `94f489c…`), `Loudness_ISO532_1.m`, GNU Octave 11.3.0. Four variants: 0.24 and 0.22 with the constant (2026-11-05 run), 0.24 and 0.22 with `ZUP = ZUP+0` (this round; one-line diffs delivered).
- MoSQITo 1.2.1 outputs of the 2026-11-05 run (shipped 0.24 and 0.22 bound at run time).
- Workbooks: the three Annex B `.xlsx` (data_only), tolerance `max(0.1, 0.05·|ref|)`; "4-decimal agreement" = |Δ| ≤ 5e-5 + 1e-9; decisive points = the 12,287 workbook points where the two C builds differ by ≥ 2e-4.
- Not read: Astra's `2026-11-06-F03-factorial-matrix-118322f/` and `2026-11-06-F03-three-implementations-118322f/`.

## 3. Method

The slope stage (`f_calc_slopes`) and temporal weighting of the C program were ported to binary64 Python (`slopes_port.py`) with three switches: F1 (`USL[12][4]`), F2 (constant added to every ZUP), F3 (all slope-stage literals rounded to binary32 first). The port is fed with iso532's own stage outputs from a Rust harness (`harness/`): for signals 6–25 the nonlinear-decay output (21 × n_time) for F4 ∈ {2√2, calibration file} × F6 ∈ {zero, MoSQITo tail}, for signals 2–5 the `zwst` core loudness, for signal 1 the core loudness of the levels.

Port validation (`validate.log`): with F2 = 0 the port reproduces iso532's N(t) within 2.1e-14 on all 20 time-varying signals and the signal-1 total to the last digit; with F2 = 1e-4 it reproduces SQAT 0.24 within 1.9e-12 on 17 signals and within 6.5e-8 on signals 11–13 (N′ within 1e-7). So the port is iso532 when the constant is off and SQAT when it is on, and every cell of the factorial is a controlled single-pipeline variant.

Full factorial on signals 6–25: F1 × F2 × F3 × F4 × F6 = 32 cells × 20 signals (+ negative control `USL[12][4] = 0.30`). Signals 2–5: F1 × F2 × F3 × F4 on the iso532 front end, SQAT's three front-end levels × F1 × F2. Signal 1: F1 × F2 × F3. In addition F2 was switched inside SQAT itself (Octave), so the attribution does not rest on the port alone.

## 4. Results

### 4.1 Implementations as shipped and with one cell changed (signals 6–25, workbook points)

| implementation | max abs | median abs | within 5e-5 / 48,711 | decisive: max / median / within 5e-5 of 12,287 | outside tolerance |
| --- | --- | --- | --- | --- | --- |
| official C 0.22 (own build) | 1.0e-4 | 0 | 45,372 | 1.0e-4 / 0 / 11,174 | 0 |
| official C 0.24 (one cell) | 1.69e-2 | 0 | 31,506 | 1.69e-2 / 5.0e-4 / 0 | 0 |
| SQAT 0.24 (shipped) | 1.69e-2 | 3.7e-5 | 31,531 | 1.69e-2 / 5.3e-4 / 0 | 0 |
| SQAT 0.22 | 7.9e-5 | 2.5e-5 | 45,487 | 6.5e-5 / 2.5e-5 / 11,224 | 0 |
| SQAT 0.30 (negative control) | 5.40e-2 | 4.0e-5 | 29,369 | 5.40e-2 / 1.7e-3 / 0 | 0 |
| MoSQITo 0.24 (shipped) | 2.29e-2 | 7.5e-5 | 19,358 | 2.29e-2 / 6.2e-4 / 93 | 0 |
| MoSQITo 0.22 | 2.33e-2 | 4.9e-5 | 24,703 | 2.33e-2 / 7.6e-5 / 4,334 | 0 |
| iso532 0.24 (shipped) | 1.69e-2 | 4.0e-5 | 29,539 | 1.69e-2 / 6.0e-4 / 0 | 0 |
| iso532 0.22 | 2.19e-4 | 3.2e-5 | 36,689 | 2.19e-4 / 6.4e-5 / 5,231 | 0 |

### 4.2 Factorial cells (iso532 pipeline + port; 2√2, zero init, binary64; F6 and F3 change nothing visible here, see 4.4)

| F1 | F2 | max abs | median abs | within 5e-5 | decisive max / median / within | vs C 0.22 CLI max / median |
| --- | --- | --- | --- | --- | --- | --- |
| 0.24 | 0 (= iso532 shipped) | 1.69e-2 | 4.0e-5 | 29,539 | 1.69e-2 / 6.0e-4 / 0 | 1.69e-2 / 4.0e-5 |
| 0.22 | 0 (= iso532 one cell) | 2.19e-4 | 3.2e-5 | 36,689 | 2.19e-4 / 6.4e-5 / 5,231 | 2.19e-4 / 3.2e-5 |
| 0.24 | 1e-4 (= SQAT shipped) | 1.69e-2 | 3.7e-5 | 31,531 | 1.69e-2 / 5.3e-4 / 0 | 1.69e-2 / 3.6e-5 |
| 0.22 | 1e-4 (= C program) | **7.9e-5** | **2.5e-5** | **45,487** | **6.5e-5 / 2.5e-5 / 11,224** | 1.0e-4 / 2.5e-5 |
| 0.30 | 1e-4 (negative control) | 5.40e-2 | 4.0e-5 | 29,369 | 5.40e-2 / 1.7e-3 / 0 | 5.41e-2 / 3.9e-5 |

The (0.22, 1e-4) cell has the same counts as SQAT 0.22 to the last point and a higher 4-decimal agreement than the own C build (45,487 vs 45,372), i.e. the port in binary64 is at least as close to the binary that produced the workbooks as a fresh MSVC build of the official source.

### 4.3 Main effects (paired cells, all 48,711 workbook points, max |Δ| over the 16 pairs of each factor)

| factor | max |Δ| | range over pairs | interpretation |
| --- | --- | --- | --- |
| F1 `USL[12][4]` 0.22 − 0.24 | 1.685e-2 | 1.685e-2 … 1.685e-2 | the decisive-point discrepancy; independent of every other factor |
| F2 constant 1e-4 − 0 | 1.788e-4 | 1.785e-4 … 1.788e-4 | the MoSQITo-lineage residual; additive with F1 (interaction ≤ 3e-7) |
| F3 binary32 literals on − off | 9.0e-7 | 9.02e-7 … 9.04e-7 | below the workbook's resolution; changes the 4-decimal agreement by 17 points |
| F4 calibration − 2√2 | 6.99e-2 | 6.987e-2 … 6.990e-2 | +0.26 % multiplicative; 4-decimal agreement collapses to 2,920 points |
| F6 MoSQITo tail − zero | 0 | 0 … 0 | inert: every Annex B signal ends in silence, so the tail seed equals the zero state |

### 4.4 F2 mechanism (cell 0.22/1e-4 minus 0.22/0, per signal)

| signal | mean F2 effect | mean 1e-4 × nm[0] | max F2 effect | corr(effect, nm[0]) |
| --- | --- | --- | --- | --- |
| 9 pink noise 0–50 dB | 1.43e-5 | 1.43e-5 | 9.8e-5 | 0.989 |
| 14 propeller aircraft | 8.00e-5 | 8.00e-5 | 1.50e-4 | 0.988 |
| 15 vehicle interior (diffuse) | 1.164e-4 | 1.164e-4 | 1.79e-4 | 0.947 |
| 16 hairdryer | 7.7e-6 | 7.7e-6 | 1.7e-5 | 0.931 |
| 17, 18, 19, 24 | 6.1e-6, 9e-7, 1.42e-5, 1e-7 | identical | 2.0e-5, 6.3e-6, 2.9e-5, 1.6e-6 | 0.95, 0.91, 0.95, 0.91 |
| 6, 7, 8, 10–13, 20–23, 25 | 0 | 0 | 0 | — |

Signal 1 (levels in, no front end): iso532 = MoSQITo = 83.29512844; SQAT = port with the constant = 83.29566116; workbook and C 83.2957. Difference 5.33e-4 = 1e-4 × nm[0] = 1e-4 × 5.3272. The 240 N′ values of the port with the constant are within 4.8e-5 of the workbook (all 240), without it 160 of 240 (slope samples shift by USL × 1e-4).

### 4.5 Stationary signals 2–5 (N error against the workbook, %)

| signal | C 0.22 | SQAT, Annex A front end, 0.2 s skip (any F1, F2) | SQAT, no skip | iso532 `zwst` / MoSQITo (any F1, F2, F3) | iso532 `zwst`, calibration conversion |
| --- | --- | --- | --- | --- | --- |
| 2 250 Hz 80 dB | 0 | +0.0001 | +0.087 | +0.234 / +0.235 | +0.382 |
| 3 1 kHz 60 dB | 0 | −0.0009 | +0.094 | +0.823 / +0.816 | +0.987 |
| 4 4 kHz 40 dB | 0 | −0.0013 | −0.0012 | +0.424 / +0.426 | +0.569 |
| 5 pink noise 60 dB | +0.0010 | +0.0005 | −0.018 | −0.767 / −0.770 | −0.611 |

F1, F2 and F3 move these cells by ≤ 0.0002 % (signal 5, F2); the error is the front end.

## 5. Hypotheses

| | verdict | evidence |
| --- | --- | --- |
| H1 F1 is the whole SQAT discrepancy | PASS | SQAT 0.22 at the rounding level; F1 effect 1.685e-2 in every pair |
| H2 F2 is the iso532/MoSQITo residual after F1 | PASS | cell (0.22, 1e-4) = SQAT 0.22 counts; residual ≈ 1e-4 × nm[0]; zero on signals without low-frequency energy |
| H3 F3 < 1e-5 and not needed | PASS | 9.0e-7; +17 points of 4-decimal agreement |
| H4 F4 multiplicative ≈ +0.15 %, kills agreement | PASS | +0.148 … +0.164 % of N on signals 2–5, 0.070 sone max on 6–25; 2,920 points within 5e-5 |
| H5 front end is the stationary error | PASS | §4.5 |
| H6 F6 affects only the first 0.5 s | PASS (stronger) | effect exactly 0 on all 20 signals |
| H7 cross-implementation identities | see §6 | SQAT(F2 = 0, 0.24) vs iso532 shipped; SQAT 0.22 vs port |

## 6. Cross-implementation identities (full 2 ms grid, not only workbook points)

- port(F2 = 0) vs iso532 0.4.0: ≤ 2.1e-14 on all 20 time-varying signals.
- port(F2 = 1e-4, 0.24) vs SQAT 0.24 (Octave, 2026-11-05): ≤ 1.9e-12 on 17 signals; 1.7e-8, 1.0e-8, 6.5e-8 on signals 11, 12, 13 (1 kHz tone pulses 50 ms / 500 ms / combined), 121–195 frames each, N′ ≤ 1.0e-7. The same three signals show the same differences for every F1/F2 combination, and SQAT with the constant removed differs from iso532 shipped by the same amounts, so this is an upstream stage (SQAT's third-octave or nonlinear-decay implementation vs iso532's) during transients, not the slope stage. It is three orders of magnitude below the workbook's resolution and was not pursued.
- SQAT(F2 = 0, 0.24) vs iso532 0.4.0 shipped and SQAT(F2 = 0, 0.22) vs port(0.22, 0): see `results.json["validation"]` (`sqat_eps0_*`), filled in §7.

## 7. SQAT runs with the constant removed (Octave 11.3.0)

Both variants ran on all 25 signals (`run-sqat-e0-024.log`, `run-sqat-e0-022.log`). Switching F2 off inside SQAT turns SQAT into iso532, and switching F1 as well turns it into the port's (0.22, 0) cell:

- SQAT(F2 = 0, 0.24) vs iso532 0.4.0 shipped, full 2 ms grid: ≤ 1.9e-12 on 17 signals; signals 11/12/13: 1.7e-08 / 1.0e-08 / 6.5e-08 (the upstream transient difference of §6, unchanged by F2). Overall max 6.5e-08.
- SQAT(F2 = 0, 0.22) vs port(0.22, F2 = 0): ≤ 1.9e-12 on 17 signals; 11/12/13: 1.7e-08 / 1.0e-08 / 6.5e-08. Overall max 6.5e-08.
- Against the workbook (signals 6–25) the constant-removed SQAT cells reproduce the iso532 cells' statistics:

| implementation | max abs | median | within 5e-5 | decisive max / median / within |
| --- | --- | --- | --- | --- |
| SQAT, constant removed, 0.24 | 1.69e-02 | 4.0e-05 | 29,539 | 1.69e-02 / 6.0e-04 / 0 |
| SQAT, constant removed, 0.22 | 2.19e-04 | 3.2e-05 | 36,689 | 2.19e-04 / 6.4e-05 / 5,231 |
| iso532 0.24 (shipped) | 1.69e-02 | 4.0e-05 | 29,539 | 1.69e-02 / 6.0e-04 / 0 |
| iso532 0.22 | 2.19e-04 | 3.2e-05 | 36,689 | 2.19e-04 / 6.4e-05 / 5,231 |

- Stationary signals 2–5 (Annex A front end, 0.2 s skip): removing the constant changes N by ≤ 0.0002 % (signal 2: +0.0001 % (with constant +0.0001 %); signal 3: -0.0009 % (with constant -0.0009 %); signal 4: -0.0013 % (with constant -0.0013 %); signal 5: +0.0004 % (with constant +0.0005 %)); the stationary agreement is a front-end property, not a slope-stage one.
- Without the constant SQAT's own C-style grid loop (`while k <= z2`) loses the sample at the band edge on most frames (signal 1: N′ max difference 0.71 against both iso532 and the workbook), which is what the constant is for in the C program; iso532 keeps the grid intact by rounding to 1e-8 instead. The N comparison above is unaffected because N is integrated analytically, not from the grid.

## 8. Findings for the project

- `iso532` 0.4.0 time-varying path = SQAT v2.0 − {F1, F2}. The two constants are independent and additive; the F2 side effect on N is 1e-4 × core loudness of band 0 (≤ 1.8e-4 sone on Annex B, ≤ 0.0014 % of N), on N′ ≤ USL × 1e-4 at slope samples. Whether iso532 should adopt the C program's constant (it is a robustness epsilon of the C grid loop whose effect on N is an artefact; iso532 obtains the same grid robustness by rounding to 1e-8) is a decision for the user, together with `USL[12][4]` = 0.22 and the ZWST front end (candidate 0.5.0 set). Adopting both makes the official program's Annex B tables reproducible to 4 decimals with unmodified golden generation.
- The 1e-4 full-sequence total threshold used in the 0.4.0 acceptance (`project-c01-root-cause`) was absorbing F2; with F2 and F1 applied, the achievable threshold against the C program is the CLI's own 4-decimal rounding (1e-4 abs) and against SQAT 1e-12.
- MoSQITo: beyond F1 and F2 the F-04…F-07 deviations keep its maximum at 0.023 sone regardless of the cell value; its stationary front end carries the 0.2–0.8 % errors.
- The workbooks were produced with the 2√2 conversion: no cell under the calibration conversion reaches 4-decimal agreement.

## 9. Limits

- F7 (MoSQITo F-04…F-07) was not toggled; its size is read off MoSQITo 0.22 vs the C cell.
- F3 was applied to the slope stage only; the C program's `0.0635f`, `1.0f`, `0.4f`, `0.32f` in the core-loudness stage were not emulated (relative effect ≈ 2e-8).
- The official CLI is the main agent's own MSVC build (provenance round); it agrees with the workbook within 1e-4 everywhere and exactly at 93.1 % of the points, so the workbook's producer was not bit-identical to this build.
- Signals 11–13: 6.5e-8 SQAT-vs-iso532 transient difference upstream of the slope stage, unexplained.
- Octave, not MATLAB, executed SQAT (MATLAB licence unavailable); SQAT uses only built-in functions on this path.

## 10. Files

`preregistration.md` / `.zh-TW.md`, `report.md` / `report.en.md`, `replay.md`, `results.json`, `calibration.json`, `slopes_port.py`, `refs.py`, `run_factorial.py`, `validate.py`, `analyze.py`, `finalize_delivery.py`, `harness.Cargo.toml.txt`, `harness.Cargo.lock.txt`, `harness.main.rs.txt`, `run_sqat_variant.m.txt`, `sqat-eps0-022.diff.txt`, `sqat-eps0-024.diff.txt`, `run-factorial.log`, `run-sqat-e0-022.log`, `run-sqat-e0-024.log`, `validate.log`, `analyze.log`, `raw-output-hashes.json`, `redaction.log`, `delivery-check.md`, `delivery-integrity.json`.
