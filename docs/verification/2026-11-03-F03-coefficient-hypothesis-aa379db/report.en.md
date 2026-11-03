# F-03: does 0.22/0.24 compensate for language or data-layout error?

Date: 2026-11-03 (Asia/Taipei). Independent experiment: Astra (gpt-6-astra). Tested snapshot: `aa379db8f3dc37f5048ac6c8b7a6d4ba2a6c3b76`. [繁體中文](report.md). No production tables, code or goldens changed; no stage/commit/push/tag.

## 1. Conclusion and scope

**The tested conditions do not support the hypothesis that 0.24 compensates for C/Python floating-point precision or correct data-layout conversion. They still cannot decide whether the ISO cell should be 0.22 or 0.24.** The source literals already differ. Single-point arithmetic computes a result conditional on a coefficient; a formula containing an unknown coefficient does not independently determine that coefficient.

| Hypothesis | Verdict | Evidence boundary |
|---|---|---|
| H_fp: coefficient difference compensates for floating-point precision | not_supported | 4 safe interior fixtures × 2 coefficients × 6 modes = 48 results; the primary coefficient effect is about 289,262 times the largest point roundoff. Finite local experiment, not a global algorithmic bound. |
| H_layout: correct layout/index conversion causes the discrepancy | not_supported | Tested layouts return the same logical cell; tagged-table controls detect wrong row, column and stride. Does not exclude indexing bugs in untested code. |
| H_intent: authors deliberately compensated | inconclusive | No corresponding author statement or commit rationale; numerical experiments cannot establish historical intent. |
| H_standard: unique correct ISO cell | inconclusive / PENDING | No authorized target cell from Table A.9 or independent identifying constraint. No production-table change follows from this experiment. |

This is a research delivery, not product-release ACCEPT or complete ISO conformity.

## 2. Exact single-point calculation

The local linear segment and trapezoid formula are supported by p.42 of the [1991 original paper](https://www.jstage.jst.go.jp/article/ast1980/12/1/12_1_39/_pdf), and the preserved C uses the same form. This round did not obtain an independent coefficient-derivation equation from the 2017 normative text. See [sources.md](sources.md) for provenance and visual-review limits.

Let starting specific loudness `N0=7/20=0.35 sone/Bark`, distance `Δz=1/5=0.2 Bark`, and slope magnitude `s`:

`N′(z0+Δz) = N0 − s·Δz`

`A = N0·Δz − s·Δz²/2`

`A` is the local segment area in sone, not full loudness. Starting and candidate endpoints all remain in `[0.30,0.42)`, corresponding to zero-based RNS row 12. The synthetic stage places it after band 4 and actually reads column 4.

| Given slope s | Exact N′, sone/Bark | Exact local A, sone |
|---|---:|---:|
| 0.22 | 0.306 = 153/500 | 0.0656 = 41/625 |
| 0.24 | 0.302 = 151/500 | 0.0652 = 163/2500 |
| Absolute difference | 0.004 | 0.0004 |

Exact Fraction calculations agree with Decimal at 80 and 120 digits. These terminating decimals are represented exactly, so convergence is exact equality. Additional `(N0,Δz)` fixtures are `(0.32,0.05)`, `(0.40,0.3)` and `(0.375,0.125)`; every segment with either coefficient remains in the same safe range.

**If the question is “without specifying the coefficient, what unique value does the ISO mathematics predict?”, the available information is insufficient to identify one.** Given N0/Δz, s/N′/A are three unknowns with two equations. Both candidate solutions satisfy their conditional equations exactly. There is no independent N′ observation or normative coefficient selecting one. Assigning 0.306 as truth and solving back to 0.22 would be circular.

## 3. Fully crossed precision and language experiment

C was compiled with MSVC 19.44.35228 x64, `/O2 /fp:strict`; measured `FLT_MANT_DIG=24`, `DBL_MANT_DIG=53`. Python 3.11.9, NumPy 2.4.4. Both coefficients were tested with C binary32, C binary64, C float literal promoted to double, Python float, NumPy float32 and NumPy float64. Points and areas were checked against the exact oracle for the same coefficient.

| Primary-point mode | N′ at s=0.22 | N′ at s=0.24 | Maximum absolute point error across both |
|---|---:|---:|---:|
| C double / Python float / NumPy float64 | 0.306 | 0.302 | 9.325873406851316e-18 |
| C float literal → double | 0.30600000023841856 | 0.3020000010728836 | 1.0728836059570312e-9 |
| C float / NumPy float32 | 0.3059999942779541 | 0.3019999861717224 | 1.3828277587890626e-8 |

Across all 4 fixtures and both coefficients, C double/Python float/NumPy float64 produce identical point and area values; C float/NumPy float32 also agree exactly. The primary maximum area error is `1.0013580322265624e-9`; maximum point error across all 48 results is `1.4543533325195312e-8`. The primary ratio is `0.004 / 1.3828277587890626e-8 = 289262.3448275862`. Results preserve exact error fractions and ULPs. ULP uses the output type; large double-ULP counts after float-literal promotion do not imply large absolute error.

The preserved C initializes a double table with `0.22f`, storing `0.2199999988079071`; substituting `0.24f` stores `0.23999999463558197`. This rounding is not a 0.02-scale change. Both coefficients work in exact/high-precision arithmetic; the tested language does not require a different coefficient to evaluate the same formula correctly.

Supplementary mechanism scale, added after the initial design: to obtain the 0.22 candidate's primary point 0.306 using s=0.24, fixed N0 requires Δz=`11/60`, changing 1/5 by `−1/60 Bark`, or `−1/12` (about −8.33%). Fixed Δz instead requires N0=`0.354`, increasing it by `0.004 sone/Bark`, or `2/175` (about 1.14%). This quantifies required compensation; it is not evidence of author intent.

## 4. Layout, boundaries and stage traces

Source inspection in [sources.md](sources.md) finds C `[18][8]` literal 0.22f versus Rust f64/local MoSQITo 1.2.1 NumPy float64 literal 0.24. Both coefficients round-trip correctly through Python nested lists, NumPy C/F-order and matching flat strides. C 2D and a copied row-major flat array agree. The tagged target `100*row+col` is 1204; negative controls return wrong-row=1104, wrong-column=1203 and wrong C-stride over F-order storage=1005. All were detected. This establishes sensitivity to the injected mistakes, not absence of every implementation bug.

Separate probes examine 0.30/0.42 and their adjacent binary64 nextafter values. Simplified index logic differs: at 0.30, C float thresholds plus initial `>=` select row13, while Rust r8 plus initial `<` selects row12; Rust's next-segment `<=` selects row13. The binary64 value immediately below 0.42 selects row12 with raw `<`, but row11 after r8 in the initial lookup. These combine literal types, operators and explicit eight-decimal rounding policy. They are not pure language errors or full-stage boundary acceptance. The primary 0.35 point is far from these thresholds.

Isolated archived Rust and preserved C were instrumented only to count target reads. The C wrapper sets the target in sequence; the Rust variants differ in only that table cell. With synthetic `nm[4]=0.35`, all other bands zero:

| Implementation | s | Target queries | Stage total N | N′[45], nominal 4.6 Bark |
|---|---:|---:|---:|---:|
| C | 0.22f | 1 | 0.810818895244731 | 0.30602200613860336 |
| C | 0.24f | 1 | 0.8046635946822402 | 0.30202400750904235 |
| Rust | 0.22 | 2 | 0.811 | 0.30600000000000016 |
| Rust | 0.24 | 2 | 0.805 | 0.30200000000000016 |
| MoSQITo Python | 0.22 | not instrumented | 0.811 | 0.30600000000000016 |
| MoSQITo Python | 0.24 | not instrumented | 0.805 | 0.30200000000000016 |

Rust counts include preparation queries; two reads do not mean two physical slope segments. C max ΔN′=`0.003997998629561017`, ΔN=`0.006155300562490806`; Rust gives `0.0040000000000000036` and `0.006000000000000005`. The negative control `nm[3]=0.35` produces zero target reads in C/Rust and identical outputs after changing the coefficient. C buffer guards remain intact and both implementations produce finite stage outputs.

C adds `.0001f` to band limits and advances samples by `0.1f`; Rust uses r8 comparisons and rounds final N to 0.001 sone at this magnitude. Consequently same-coefficient stage residuals are not entirely floating-point effects. Stage total N is not local A. These traces demonstrate actual target activation alongside the independent local oracle; C parity does not decide the standard.

The actual saved MoSQITo 1.2.1 `_calc_slopes` was also run in isolation with input shape `(21,1)`. Its `_get_rns_index` helper source stays unchanged; the package import is removed and supplied through an isolated namespace. Only the 0.22 variant changes the target literal; diffs and helper hash are retained. Both variants produce N shape `(1,)`, N′ shape `(240,1)`, all finite. Band4 ΔN′ and ΔN are `0.0040000000000000036` and `0.006000000000000005`; the band3 negative control is unchanged. This tests the actual Python stage without claiming Python lookup-count instrumentation or a complete audio pipeline rerun. Both C and Python respond to the coefficient; different source literals are not simply required by their programming languages.

## 5. Gates, authority and delivery

| Gate | Result |
|---|---|
| Exact Fraction and Decimal 80/120 oracle | passed |
| 48 coefficient×precision×interior results and same-coefficient language parity | passed |
| Layout positive and injected-error negative controls | passed |
| Simplified boundary diagnostic | passed (comparison-policy differences observed; not full boundary acceptance) |
| Isolated C/Rust target activation, negative controls, finite/guards | passed |
| Actual isolated MoSQITo stage, shape/finite, coefficient effect and band3 negative control | passed |
| Normative target cell and historical intent | PENDING / inconclusive |
| Full product cargo suite, benchmarks, complete audio/Annex B | not_run; outside scope |

The [ISO catalog](https://www.iso.org/standard/63077.html) and [ANSI public preview](https://webstore.ansi.org/preview-pages/ISO/preview_ISO%2B532-1-2017.pdf) support a November 2017 A.9 correction and describe the reference software's normative role. They do not provide the target cell or an independent derivation. The preserved C attachment's correspondence to the corrected edition is unproved. The historical 1991 program's 0.22 is primary provenance, not automatically the 2017 normative value.

[design.md](design.md)/[design.en.md](design.en.md) preceded execution. Initial execution passed. A second run corrected source locations and added the compensation-scale diagnostic; a third adds the actual isolated MoSQITo stage, with a new tmp directory for each run. Delivered results correspond to the third run. `results.json` preserves individual results, source/derived/binary hashes and verdicts. `run-log.json` records commands and stdout/stderr. Diff files show instrumentation and single-cell changes. Complete source copies and binaries stay in tmp; delivery is UTF-8 text only.

MSVC environment setup warned that `vswhere.exe` was not on PATH, then successfully initialized x64, compiled both C executables and ran them. The warning is retained rather than hidden.

Reproduce on Windows with MSVC x64, Python+NumPy and rustc: from the repo run `python <delivery>/run_experiment.py --work <new-tmp-directory> --out <new-results.json> --official-c <preserved-ISO_532-1.c> --official-header <preserved-ISO_532-1.h> --mosqito-source <preserved-_calc_slopes.py> --vcvars <vcvars64.bat>`. The script verifies the C hash, archives fixed-commit Rust, refuses existing work/results, and records versions, commands and scoped assertions. Previously lawfully saved C and local Python sources remain prerequisites; git alone does not supply the external attachment.

See [delivery-check.md](delivery-check.md) for redaction, integrity and explicit handling of unrecognized suffixes. The production table-change gate remains PENDING.

After review, a read-only `cl /Bv` version probe was added (no source supplied, expected D8003/exit 2), and the runner/results MoSQITo gate field was synchronized. This is not a failed compilation; DSP was not rerun for metadata-only changes. Environment/log records explicitly identify the probe and its purpose.
