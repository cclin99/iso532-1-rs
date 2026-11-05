# Why the Annex B comparison is consistently about 0.15% high

> 對照／Pair: [中文版](report.md) · source: zh · synced 2026-11-05

Claude (Opus 5.5, main agent, not Astra), 2026-11-05 Asia/Taipei. Tested: `v0.4.0` = `118322f` (0.4.0 wheel, the Rust outputs of the 2026-11-04 Astra round) and the CLI of the official Annex A C program. Follows up §4.2 of [`2026-11-05-perf-compliance-118322f/`](../2026-11-05-perf-compliance-118322f/report.en.md).

## Conclusions

- **The bias does not come from the engine; it comes from the convention used to convert WAV samples to sound pressure.** The Annex B workbook references match the fixed conversion "digital full scale 1.0 = 2√2 Pa" (a full-scale sine = 100 dB SPL) exactly. The Annex C calibration file `calibration signal sine 1kHz 60dB.wav` peaks at only 327 LSB, where the same convention gives 327.68 LSB, so its RMS is **0.0226 dB** below the stated 60 dB.
- The official CLI derives its factor from the whole-file mean square of the calibration file (2.835798 Pa per unit, 0.26% above 2√2), and so did the Astra acceptance harness and `compliance.py` of the previous report. Every level is therefore 0.0226 dB high, and **loudness is consistently about 0.15% high**.
- With the 2√2 conversion, the median N(t) deviation of the 20 time-varying signals is 0.000% to −0.007%, Nmax deviates by ≤ 0.004%, and the pure-tone stationary signals 2 and 4 by −0.001%. The per-point rule still has 0 points outside.
- The repository's own Annex B tests (`tools/gen_golden.py` → `data/annexb` → `tests/annexb.rs`) already use `wav_calib=2 * 2**0.5`, as do the MoSQITo 1.2.1 tests, so they are not affected. The 0.4.0 C golden (`tools/gen_golden_c.py`) uses the calibration file like the official CLI; Rust and C read the same input there, so that comparison is not affected either.
- **No code change is needed.** The engine takes sound pressure in Pa, and the conversion is the integrator's responsibility (README "Current boundaries"). What is open is which conversion the project uses for its external Annex B comparisons, and whether to document the 0.0226 dB difference.

## 1. Elimination

| step | result | evidence |
|---|---|---|
| Rust against official C (same calibrated input) | N5 differs by ≤ 4.5e-4 sone; both are +0.14% to +0.18% against the workbook | `official_c_linear_same_rows` in the earlier `AnnexB深入分析.json` (`docs/verification/2026-10-31-F02-5450d39/`); the official CLI reads the WAV and the calibration file itself |
| Skipping WAV and filter bank (signal 1, third-octave levels as input) | N deviates by −0.0007% | previous report §4.1 |
| Official C stationary path (signals 2–5, time skip 0.2 s) | +0.142% to +0.162% | [official-cli/](official-cli/), [stationary-compare.json](stationary-compare.json) |
| Steady part of the official C time-varying path (pure tones 2–4) | +0.142% to +0.189% | same |
| Bias against reference loudness | about +0.15% constant for tones; larger for noise and at low loudness (signal 9: +0.36% at 0.3–1 sone) | [bias-vs-level.json](bias-vs-level.json): the signature of a level offset (the loudness curve is steeper near threshold) |
| Level after calibrating with the official calibration file | the calibration file is 60.000 dB in every part; signal 2 is 80.023 dB, signal 3 60.028 dB | [level-check.json](level-check.json) |

The bias therefore arises at the WAV → calibration step. The calibration code of the official CLI (`CalFactor = sqrt(10^(L/10)·I_REF/IntensSum)` in `ISO_532-1_main.c`) does what we do; the calibration file itself is inconsistent with the conversion behind the workbooks.

## 2. Calibration file numbers

- 48 kHz, 16 bit, mono, 1.000 s; integer peak ±327, RMS 231.1025 LSB.
- Under the 2√2 convention, a 60 dB 1 kHz sine peaks at 0.01 = 327.68 LSB with RMS 231.7048 LSB.
- RMS ratio: −0.02261 dB. Conversion ratio 2√2 / 2.835798 = 0.997401 (−0.260%).
- Stated levels recovered with 2√2: signal 2 "250 Hz 80 dB" is 80.0003 dB, signal 3 "1 kHz 60 dB" is 60.005 dB; with the calibration file they are 80.023 dB and 60.028 dB. (Signal 4 "4 kHz 40 dB" comes out about 0.05 to 0.07 dB low either way, unrelated to this bias.)

A peak of 327 looks like 327.68 truncated to an integer. This is an inference; the official material does not say how the calibration file was produced.

## 3. Hypothesis test ([rescale_test.py](rescale_test.py), 0.4.0 wheel)

The Astra calibrated inputs were multiplied by 0.997401 (that is, converted with 2√2), recomputed and compared with the workbooks ([rescale-test.json](rescale-test.json)):

| signals | median N(t) deviation (calibration file → 2√2) | Nmax deviation (calibration file → 2√2) |
|---|---|---|
| 6–13 (B.4 synthetic) | +0.145% to +0.165% → −0.000% to +0.000% | +0.141% to +0.166% → −0.000% to +0.001% |
| 14–25 (B.5 technical) | +0.139% to +0.183% → −0.007% to +0.000% | +0.140% to +0.170% → −0.004% to +0.000% |
| 2, 4 (pure tones, time-varying steady part) | +0.146% / +0.144% → −0.001% / −0.001% | — |

The N(t) median counts only points with reference ≥ 0.5 sone. With either conversion, time-varying N(t) has 0 points outside the per-point rule.

## 4. Impact and options

- The engine, the 0.4.0 release and the Annex B PASS are unchanged: both conversions pass, and the 2√2 conversion leaves larger margins.
- The statement "consistently about 0.15% high" in §4.2 of the previous report stays correct, but now has a cause: the conversion convention, not an engine error. This report is the supplement to that section; the previous delivery is not modified.
- Open (not handled in this round):
  1. Whether external Annex B comparisons (acceptance harnesses, future reports) switch to 2√2 or list both.
  2. Whether the README precision section and the description of `tools/gen_golden_c.py` should state the 0.0226 dB difference between the two conversions.
  3. Whether `tools/gen_golden_c.py` should switch to 2√2. That changes the C golden input and requires regenerating every C golden hash, i.e. a separate round.

## 5. Limits

- "The workbooks were produced with 2√2" is inferred from the fit (the deviation drops to 0.000%); the official material does not state it.
- Only time-varying N(t) and Nmax were compared; the specific loudness of all 73,116 points was not recomputed with 2√2.
- The official CLI is the one built in an earlier round (its hash matches the C-01 zero-pad record); it was not recompiled.

## 6. Evidence files

| file | content |
|---|---|
| [official-cli/](official-cli/) | official CLI stationary and time-varying output for signals 2–5 (`Loudness.csv`, stdout), commands, input hashes; the time-varying `SpecLoudness.csv` files are 8 MB each and only hashed |
| [stationary_compare.py](stationary_compare.py), [stationary-compare.json](stationary-compare.json) | official C stationary and time-varying steady part against the workbook |
| [bias_vs_level.py](bias_vs_level.py), [bias-vs-level.json](bias-vs-level.json) | bias grouped by reference loudness |
| [level_check.py](level_check.py), [level-check.json](level-check.json) | actual levels after calibration |
| [rescale_test.py](rescale_test.py), [rescale-test.json](rescale-test.json) | test of the 2√2 hypothesis |
| [delivery-integrity.json](delivery-integrity.json) | SHA-256 of each file after redaction (excluding itself) |
