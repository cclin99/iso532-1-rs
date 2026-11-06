# Preregistration: factor attribution of the Annex B errors of MoSQITo, iso532, SQAT and the official C program

Main agent (Claude), 2026-11-06 (Asia/Taipei). Frozen snapshot: `62e8559` (the `iso532` crate is byte-identical to `v0.4.0` = `118322f`; `git diff 118322f HEAD -- iso532/` is empty). Written before the factorial runs; the diagnostics that motivated H2 are listed in §4 so that confirmatory and exploratory results stay apart. Astra's parallel round (`docs/verification/2026-11-06-F03-factorial-matrix-118322f/`, in progress) was not read.

## 1. Question

After setting `USL[12][4]` to 0.22, SQAT v2.0 agrees with the Annex B workbooks to the 4-decimal rounding level (decisive points: max 6.5e-5), but iso532 0.4.0 still differs by up to 2.2e-4 (signals 9, 14, 15) and MoSQITo 1.2.1 by up to 0.023. Which implementation factors, alone and in combination, account for each implementation's error against the workbooks (which were produced by the official C program, see `2026-11-05-F03-workbook-provenance-118322f`)?

## 2. Factors and levels

| id | factor | levels | who has what |
|---|---|---|---|
| F1 | `USL[12][4]` | 0.24 / 0.22 | C 0.22; SQAT, MoSQITo, iso532 0.24 |
| F2 | band-edge constant added to every ZUP (`_ZUP += .0001f`, C line 862; SQAT line 528) | 0 / 1e-4 Bark | C, SQAT 1e-4; MoSQITo, iso532 0 |
| F3 | slope-stage literals rounded to binary32 (`0.9f`, `0.1f`, `.0001f`, table entries) | off / on | C on (tables declared `double`, written as `float` literals); SQAT, MoSQITo, iso532 off |
| F4 | pressure conversion of the int16 WAVs | 2√2 Pa per full scale / Annex C calibration file (ratio 1.0026058976668580, +0.0226 dB) | workbooks 2√2 (provenance round); the brief's conversion (b) is the calibration file |
| F5 | stationary front end (signals 2–5) | Annex A filter bank, 0.2 s skip (C, SQAT) / Annex A filter bank, no skip (SQAT `time_skip=0`) / MoSQITo Butterworth-FFT third-octave spectrum (MoSQITo, iso532 `zwst`) | |
| F6 | nonlinear-decay initial state (signals 6–25) | zero (C, SQAT, iso532 0.4.0) / MoSQITo tail seed (MoSQITo, iso532 `NlInit::MosqitoTail`) | |
| F7 | MoSQITo-lineage slope/temporal deviations F-04…F-07 | not toggleable here; measured as MoSQITo − port(F6 = tail, F2 = 0) | |

F1–F3 are toggled in a binary64 Python port of the official `f_calc_slopes` + temporal weighting (`slopes_port.py`) fed with iso532's own nonlinear-decay output (`harness/`, shipped tables); F4 and F6 are toggled in the Rust harness; F5 uses SQAT (Octave) and the iso532 `zwst` front end. F2 is additionally toggled inside SQAT itself (`sqat/var-e0-0{22,24}`, Octave 11.3.0) so that the attribution does not rest on the port alone.

Full factorial on signals 6–25: F1 × F2 × F3 × F4 × F6 = 32 cells × 20 signals. Signals 2–5: F1 × F2 × F3 × F4 on the iso532 front end, plus SQAT's three front-end levels × F1 × F2. Signal 1: F1 × F2 × F3 (levels are the input).

## 3. Hypotheses (confirmatory)

- H1 F1 alone moves N(t) by up to 0.017 sone at the 12,287 decisive points and is the whole SQAT-vs-workbook discrepancy (SQAT: 0.24 → 0.22 brings the decisive points to ≤ 1e-4).
- H2 F2 is the iso532/MoSQITo-vs-C residual that survives F1: with F2 = 1e-4 the port reproduces SQAT (same F1) to ≤ 1e-12 and the workbook to the 4-decimal level on all 25 signals; with F2 = 0 the residual is ≈ 1e-4 × core loudness of band 0 (plus ≤ USL × 1e-4 on slope samples), i.e. largest on low-frequency-heavy signals (9, 14, 15) and negligible on 6–8, 10–13, 16–25.
- H3 F3 changes N by < 1e-5 sone (relative ≈ 5e-8) and is not needed to reach the workbook's 4-decimal agreement; it may change the number of exact 4-decimal matches with the C CLI by a few per cent.
- H4 F4 scales N by ≈ +0.15 % on every signal (multiplicative, independent of F1–F3, F6); under the calibration convention no cell matches the workbook at the 4-decimal level.
- H5 F5: the MoSQITo Butterworth front end is the 0.2–0.8 % stationary error (zwst root-cause round); SQAT's Annex A front end with 0.2 s skip is at the rounding level; `time_skip = 0` moves N by ≤ 0.1 %.
- H6 F6 affects only the first ≈ 0.5 s of signals whose start is quiet and nothing at the decisive points after that.
- H7 Cross-implementation identities: SQAT(F2 = 0, F1 = 0.24) ≡ iso532 0.4.0 shipped to ≤ 1e-12 on N(t) for signals 6–25 (the two implementations differ in exactly F1 and F2 on the time-varying path); SQAT(F2 = 1e-4, F1 = 0.22) ≡ port(0.22, 1e-4) ≤ 1e-12.

Negative control: USL[12][4] = 0.30 in the port must give errors an order of magnitude above every other cell (SQAT 0.30 from 2026-11-05: 0.054).

## 4. Diagnostics already done (exploratory, before this file)

- 2026-11-05/06 runs (`tmp/impl-2026-11-05/`): per-implementation errors at 0.22/0.24 (analysis.json).
- Signal 1 (pure table path, identical input levels): C/SQAT/workbook 83.2957; iso532 = MoSQITo 83.29513 (spec differences only at slope samples).
- Source reading: C line 862 and SQAT line 528 add 1e-4 to ZUP; iso532/MoSQITo do not. 1e-4 × nm[0] (5.327) = 5.3e-4 = the signal-1 gap.
- Octave smoke test: SQAT with the constant removed gives 83.29512844 on signal 1, equal to iso532.
- Port validation (`validate` block): eps = 0 → iso532 N(t) within 5.3e-15 (6, 16, 18); eps = 1e-4 → SQAT 0.24 within 4.2e-13 (N) / 2.1e-13 (spec).

## 5. Metrics

Workbook reference (2√2 convention, `openpyxl`, data_only), as in the 2026-11-05 analysis: stationary N and 240 N′; time-varying N(t) at the workbook times, Nmax, N5 by the workbook formula, N′(t) at the designated Bark (6–13); tolerance `max(0.1, 0.05·|ref|)`; decisive points = official C 0.22 vs 0.24 CLI differ ≥ 2e-4 (12,287 points); "4-decimal agreement" = |x − ref| ≤ 5e-5 + 1e-9. Effect of a factor = cell with the factor on minus the same cell with it off, max |Δ| over all workbook points and count of points moved ≥ 1e-9.

## 6. Delivery

`docs/verification/2026-11-06-F03-factor-attribution-118322f/` (report.md / report.en.md, results.json, scripts, logs, this file); redacted with `tools/redact_paths.py` + `--check` before staging; `delivery-integrity.json` over the redacted files, excluding itself. Octave/SQAT raw outputs and WAV-derived binaries stay out of the repository (hashes only).
