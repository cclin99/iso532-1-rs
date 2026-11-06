# Independent F-03 and stationary frontend verification

> [繁體中文](report.md) · Astra (`gpt-6-astra`) · 2026-11-05 Asia/Taipei

Tested product: `v0.4.0`, `118322f8300dc752f1d38a79db230a2db5ff2870`. Fresh C CLI/DLL builds and an independent Rust harness recomputed original WAV/XLSX material. Product DSP, tests, tables and goldens were not changed. No commit, push or release was performed.

## Decisions

| Item | Status | Independent result |
|---|---|---|
| Workbook precision agreement of 0.22 | PASS | All original 49,675 points differ by ≤1e-4; all 72,875 points after adding time-varying N′ do too |
| Decisive count and exact matches | PASS | 12,287 points; 11,174 equal 0.22, zero equal 0.24 |
| Opus: 12,109 points closer to 0.22 | FAIL | Correct count 12,062; 225 ties, none closer to 0.24. Binary-float comparison misclassified 47 ties |
| Large stationary total-loudness improvement | PASS, bounded | At fixed 2sqrt2, current noct→Annex with 0.2 s skip improves absolute error 317–2,922x; filter-only with both skips 0.2 s improves 317–2,062x |
| All four total errors ≤0.001% | FAIL, strict claim | Signal 4 is −0.001337644%; the other three pass |
| Skip effect ≤0.002%, hence negligible | FAIL, attribution method | Preserving filter history, Annex signal 3 changes −0.094881% from skip 0 to 0.2 s; the old test cropped input and restarted filters |
| Candidate versus same-input C N/N′ within 1e-4 | PARTIAL | All total N pass; signal 2 N′ differs by 0.000150004 at 2.9 Bark, persisting with identical backend input levels |
| Separate approximately +0.15% calibration bias | PASS, four stationary signals | Calibration-WAV scaling adds +0.1426 to +0.1629 percentage points relative to workbook N under the Annex method |
| Corrected-2017-11 Table A.9 authority | PENDING | No page-level text obtained; numeric agreement cannot replace formal authority |
| Historical generation, generalization, public API/release acceptance | PENDING/unmeasured | Not established by this experiment |

FAIL denotes a precise claim or preregistered gate, **not a product regression or complete ISO nonconformance**. In particular, this round's 1e-4 N′ claim gate must not replace previous full-series 3e-4 or other acceptance thresholds.

## 1. Frozen inputs, fresh computation and alignment

[Preregistration](preregistration.md) and [frozen manifest](frozen-inputs.json) cover 39 original material files and 44 product files. Git showed no crate difference from the tag, but some working files used CRLF. A byte-exact `git show` extraction was therefore built in isolation. The actual dependency lock, tool versions and binary hashes are delivered. No pre-existing wheel or CLI supplied the new numbers.

Original C SHA-256 starts `a74b45ed`; the isolated, single-cell `USL[12][4]` variant starts `739af24d`. [builds.json](builds.json) holds complete hashes. Both used identical MSVC `/O2 /fp:precise` settings. Full original C is not redistributed. Frozen hashes were checked before computation.

All 24 PCM16 WAVs were freshly converted using `int16/32768 × 2sqrt2` to float32 Pa. Signals 2–5 used stationary mode and 0.2 s skip; 6–25 used time-varying mode, diffuse for 15 and free field otherwise. Workbooks were opened read-only with cached numeric values, never saved. The conditional-formatting warning does not alter these read values.

Integer 0.0001 s ticks enforce exact alignment, a 0.002 s grid, unique timestamps and full coverage, without interpolation or clipped indices. Direct C DLL output is at 2 kHz and uses frame=time_tick/5; the CLI presents 2 ms samples. Every workbook time row was matched; all 20 signals have zero unmatched CLI tail rows. [alignment.json](alignment.json) records actual, sometimes non-divisible-by-24/96 input lengths; no padding was substituted.

Stationary coverage includes N and all 240 N′ bins for each of four WAVs. Added coverage is 23,200 N′ points for signals 6–13 at the workbook's specified Bark coordinate (2.5, 8.5 or 17.5). Those added traces are identical between USL variants and within 1e-4 of the workbooks: **they cannot discriminate the disputed cell**. This is not every Bark at every time. A separate signal-1 bypass control adds 241 round4-exact workbook points outside the primary 72,875 count.

## 2. F-03 and the floating-point tie error

[Workbook comparison](workbook-comparison.json) and [summary](summary.json): 15,801 of the original 49,675 points differ between variants; 14,277 of those equal 0.22 and 411 equal 0.24. All 411 are one-last-digit separations. Maximum workbook errors are 0.0001 for 0.22 and 0.0169 for 0.24 (signal 6).

| Variant separation (sone) | Decisive points | Equal 0.22 | Equal 0.24 | Closer to 0.22 | Ties |
|---|---:|---:|---:|---:|---:|
| 0.0002 | 12,287 | 11,174 | 0 | 12,062 | 225 |
| 0.0003 | 9,940 | 9,052 | 0 | 9,940 | 0 |
| 0.0005 | 6,930 | 6,335 | 0 | 6,930 | 0 |

[rounding-audit.json](rounding-audit.json) reproduces the legacy 12,109 count from fresh CSVs. Comparing integer ten-thousandths instead identifies 47 exact decimal ties. The legacy `>=2e-4-1e-9` selection mask did not miss the boundary; the later binary-float `d22<d24` predicate was the problem. Correct closer fraction: 98.17%, not 98.6%. The data still strongly favor **0.22 as the better match to these preserved workbooks**.

Agreement cannot prove which program historically generated the workbook. C and XLSX share preserved attachment provenance; independence has not been established. The ISO_DIS/2016 marking and relationship to corrected 2017-11 remain unresolved. Product coefficients and goldens must not be changed on the authority of this numerical result alone.

## 3. Frontend × calibration matrix and filter-only effect

Values are sone, with signed workbook-relative error in parentheses. Noct denotes the current full-input RMS, skip 0; Annex retains full filter history and skips 0.2 s before RMS. Both use the same tag Rust main/slopes backend (USL=0.24). Thus this primary matrix compares complete **frontend methods**, including RMS interval; its full delta is not filter-only.

| Signal | noct, 2sqrt2 | Annex, 2sqrt2 | noct, calibration WAV | Annex, calibration WAV |
|---|---:|---:|---:|---:|
| 2 | 14.688844138 (+0.2343590%) | 14.654511753 (+0.0000802%) | 14.710487648 (+0.3820509%) | 14.676110397 (+0.1474659%) |
| 3 | 4.052275679 (+0.8229419%) | 4.019162190 (-0.0009407%) | 4.058876445 (+0.9871727%) | 4.025708040 (+0.1619238%) |
| 4 | 1.555970413 (+0.4240617%) | 1.549379275 (-0.0013376%) | 1.558216132 (+0.5690029%) | 1.551615736 (+0.1430060%) |
| 5 | 10.417333656 (-0.7665067%) | 10.497838585 (+0.0003676%) | 10.433634253 (-0.6112304%) | 10.514258392 (+0.1567794%) |

[factorial.json](factorial.json) records absolute/relative errors, improvement factors and matched-skip matrices under both calibrations. With fixed 2sqrt2, the following separates method changes from same-skip filter changes (Annex−noct, sone):

| Signal | Method delta, 2sqrt2 | Filter delta, same skip 0.2 s | Filter delta, same skip 0 s | Absolute-error improvement, same skip 0.2 s |
|---|---:|---:|---:|---:|
| 2 | -0.034332385 | -0.024222750 | -0.021522886 | 2061.9x |
| 3 | -0.033113490 | -0.029742384 | -0.029300086 | 785.6x |
| 4 | -0.006591138 | -0.006592722 | -0.006589016 | 317.1x |
| 5 | +0.080504928 | +0.078700524 | +0.078572114 | 2038.7x |

Signal 4 gives Annex N=1.54937927455 versus workbook 1.5494: absolute difference 0.00002072545, relative −0.001337644%. Displaying this as −0.001% cannot establish `≤0.001%`; the gate was not relaxed. The residual is also near workbook quantization resolution and does not establish failure of full ISO tolerance.

The calibration-WAV coefficient is 2.835797716391 Pa/FS versus 2.82842712474619 for 2sqrt2, a 0.022605099 dB offset. With fixed Annex method, calibration-only ΔN for signals 2–5 is +0.021598644, +0.006545850, +0.002236461 and +0.016419807 sone. It is not a filter benefit. The method/calibration interaction is nonzero: −4.4866e-5, −5.4916e-5, −9.2579e-6, +1.1921e-4 sone. Separate stages do not imply unrelated final outputs.

## 4. Skip, backend residuals and controls

The old `noct_skip0p2` cropped 9,600 input samples and restarted the filters. It did not discard the first 0.2 s of the same filtered output. [skip-and-band-sensitivity.json](skip-and-band-sensitivity.json) records both interpretations, testing 0, 0.1, 0.2 and 0.4 s. True full-filter RMS changes from skip 0 to 0.2 s are:

| Signal | noct | Annex |
|---|---:|---:|
| 2 | −0.068873% | −0.087410% |
| 3 | −0.083260% | −0.094881% |
| 4 | +0.000102% | −0.000137% |
| 5 | +0.017318% | +0.018412% |

This does not negate the filter effect, but disproves the negligible-interval claim. Without skip, Annex errors are still +0.087490% for signal 2 and +0.093939% for signal 3; the claimed near-workbook result depends on skip selection.

[c-fullprecision-controls.json](c-fullprecision-controls.json) verifies extremely close Annex frontend levels against original C on double-Pa input; maximum total-N difference over the four signals is about 1.59e-5 sone. Signal 2 at 2.9 Bark has a 0.00015000364 N′ residual, retained when exactly the same 28 levels enter the C backend. A downstream residual therefore exists: not all N/N′ error comes from the frontend. Both C USL variants are identical on these four stationary signals, so this residual is not the disputed F-03 cell. Further backend numerical root-cause analysis was outside scope.

| Control | Outcome and boundary |
|---|---|
| Wrong calibration / shifted time | Calibration-WAV scaling moves all four Annex results away from workbooks; deliberate one-frame (2 ms) displacement breaks precision on nonconstant N; per-signal metrics retained |
| USL-insensitive / frontend bypass | Signal 1, all-zero-dB levels and a single 1 kHz 60 dB band give identical C variants; signal 1 matches all 241 workbook round4 values |
| Length / empty RMS | Real signal-3 prefixes of 4,800, 9,600 and 19,200 samples × four skips, 12 cases; skip≥length is rejected by the harness and returns −4 in C; not public-API acceptance |
| Single-band substitution | All 28 levels and per-band ΔN retained. Sums are not strictly additive: discrepancy 0.0009061 for signal 2 and 0.0004158 sone for signal 5 in the original method comparison |
| Float32 input quantization | Direct f32 C reproduces CLI round4 for 6/9/14/15; f64↔f32 changes 1/9/11 rounded results in 9/14/15. Signal 14 maximum N delta is 8.42e-5 |
| Theoretical response / equivalent noise bandwidth | SKIPPED: not all prior ENBW/bilinear assertions were recomputed. Actual noct runs include decimation; a theory curve omitting it cannot establish the complete mechanism generally |

The assertion that float32 has no fourth-decimal impact is false. Yet many workbook discrepancies remain on signals 6 and 9 with f64 input, so quantization does not by itself explain every residual. See [float-precision-controls.json](float-precision-controls.json). These are four representative controls, not all-input proof.

## 5. Evidence strength and delivery

The four Annex B stationary WAVs show large total-loudness improvement at the specified scaling and skip. The data do not establish universal improvement, exclusively frontend error, historical workbook generation, or corrected Table A.9 authority. Calibration, frontend, skip and USL must be distinguished; a zero USL effect in limited signals does not prove universal absence of interactions.

[replay.md](replay.md) provides reproduction commands; [delivery-check.md](delivery-check.md) records environment repair, redaction and integrity checks. Original WAV/XLSX/full C and large outputs remain in tmp; delivery hashes do not substitute for original files. No unrelated performance or full-release testing was performed.
