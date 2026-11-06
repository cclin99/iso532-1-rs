# F03 — native SQAT, MoSQITo and official-C error at USL[12][4]

**Numerical execution complete:** all three native implementations, both coefficient variants, all 24 Annex WAV signals (2–25) plus level-input case 1. Started 2026-11-05; completed 2026-11-06T00:13:28.305430+08:00. Product snapshot `118322f8300dc752f1d38a79db230a2db5ff2870`; repository HEAD `493fd595ef62aaded72ed57af1a75327ba14a5b0`. No product, formal test, golden, commit or push was changed.

The coefficient differs by **0.02**, or **9.090909% of 0.22**. This is a slope-coefficient difference, **not a loudness percentage error**. For a real common-input slope case, changing the cell from 0.22 to 0.24 within each implementation changes unweighted N by approximately **−0.016866 sone in SQAT and official C**, and **−0.017 sone in MoSQITo with its native rounding**. These are within-implementation cell effects; discrepancies from the official-C baseline are listed separately in the common-input table. Public end-to-end maximum cell effects are in the second table below.

Three quantities are kept separate: (1) original baseline discrepancy from the supplied rounded official workbooks, (2) original baseline discrepancy from freshly computed full-precision official C, and (3) the difference between two native runs that change only USL[12][4]. Baselines are SQAT=.24, MoSQITo=.24, official C=.22. Counterfactuals reverse that one cell. Baseline discrepancies also contain frontend, numerical-constant, sampling-boundary and rounding effects; they cannot all be assigned to USL.

## Baseline versus supplied official workbook values

| Implementation | max \|ΔN\|, sone | RMS ΔN, sone | max \|ΔN′\|, sone/Bark | max \|ΔN\| location |
|---|---|---|---|---|
| SQAT v2.0 / Octave 8.4.0 | 0.0168838908734 | 0.00202358898472 | 5.35405607121e-05 | sig6 @ 6.8200 s |
| MoSQITo 1.2.1 / Python | 0.0808 | 0.00211862016789 | 0.0395908676514 | sig5 @ 0.0000 s |
| Official C / MSVC | 8.05072623393e-05 | 3.01327304954e-05 | 5.36754530822e-05 | sig16 @ 1.1000 s |

## Native single-cell effect: 0.24 minus 0.22

| Implementation | max \|N(.24)−N(.22)\|, sone | RMS ΔN, sone | max \|ΔN′\|, sone/Bark | max \|ΔN\| location |
|---|---|---|---|---|
| SQAT v2.0 / Octave 8.4.0 | 0.0168514726032 | 0.00202478380181 | 0.00999557966297 | sig6 @ 6.8400 s |
| MoSQITo 1.2.1 / Python | 0.0168983166682 | 0.00202442000558 | 0.0154062754797 | sig6 @ 6.7220 s |
| Official C / MSVC | 0.0168514660219 | 0.00202486611005 | 0.00999557577141 | sig6 @ 6.8400 s |

## Input groups: N discrepancies in sone

| Implementation | Input group | baseline max \|ΔN\| vs workbook | baseline RMS ΔN | cell max \|ΔN\| |
|---|---|---|---|---|
| SQAT v2.0 / Octave 8.4.0 | 1: levels | 3.88410476404e-05 | 3.88410476404e-05 | 0 |
| SQAT v2.0 / Octave 8.4.0 | 2–5: stationary | 5.39941774438e-05 | 3.50452428047e-05 | 0 |
| SQAT v2.0 / Octave 8.4.0 | 6–25: time varying | 0.0168838908734 | 0.00202369280636 | 0.0168514726032 |
| MoSQITo 1.2.1 / Python | 1: levels | 0.0043 | 0.0043 | 0 |
| MoSQITo 1.2.1 / Python | 2–5: stationary | 0.0808 | 0.047006090031 | 0 |
| MoSQITo 1.2.1 / Python | 6–25: time varying | 0.0228893512431 | 0.00207537686982 | 0.0168983166682 |
| Official C / MSVC | 1: levels | 3.9575637814e-05 | 3.9575637814e-05 | 0 |
| Official C / MSVC | 2–5: stationary | 5.43889610789e-05 | 3.5301821958e-05 | 0 |
| Official C / MSVC | 6–25: time varying | 8.05072623393e-05 | 3.0132045379e-05 | 0.0168514660219 |

## Same exact real-signal 21-band core vector

| Implementation | N(.22) | N(.24) | original baseline N − C(.22) | own cell signed ΔN | cell max \|ΔN′\| @ 5.4 Bark |
|---|---|---|---|---|---|
| SQAT v2.0 / Octave 8.4.0 | 4.39262221003 | 4.37575618046 | -0.0168660414643 | -0.0168660295669 | 0.00999041974926 |
| MoSQITo 1.2.1 / Python | 4.393 | 4.376 | -0.0166222219257 | -0.017 | 0.00998541974926 |
| Official C / MSVC | 4.39262222193 | 4.37575619911 | 0 | -0.0168660228128 | 0.00999040666562 |

## Synthetic same-input slope case

| Implementation | N(.22) | N(.24) | signed whole-pattern ΔN | \|ΔN′\| @ 4.6 Bark |
|---|---|---|---|---|
| SQAT v2.0 / Octave 8.4.0 | 0.810818850267 | 0.804663547237 | -0.0061553030303 | 0.003998 |
| MoSQITo 1.2.1 / Python | 0.811 | 0.805 | -0.006 | 0.004 |
| Official C / MSVC | 0.810818895245 | 0.804663594682 | -0.00615530056249 | 0.00399799862956 |

## Full-precision comparison with unmodified official C

| Implementation | baseline max \|ΔN\| vs C(.22) | baseline max \|ΔN′\| vs C(.22) | counterfactual max \|ΔN\| vs C(.22) | counterfactual max \|ΔN′\| vs C(.22) |
|---|---|---|---|---|
| SQAT v2.0 / Octave 8.4.0 | 0.0168516486327 | 0.00999558701527 | 2.02912656277e-06 | 1.23580166012e-06 |
| MoSQITo 1.2.1 / Python | 0.0808543889611 | 0.0717794727493 | 0.0808543889611 | 0.0717794727493 |
| Official C / MSVC | 0 | 0 | 0.0168514660219 | 0.00999557577141 |

## Relative N metrics and affected coordinates

| Implementation | workbook max N error %, \|ref\|≥1e−4 | workbook max N error %, \|ref\|≥1 | cell max N change %, \|N(.22)\|≥1 | cell changed N points (>1e−12) |
|---|---|---|---|---|
| SQAT v2.0 / Octave 8.4.0 | 49.9015902272 | 0.478807222633 | 0.47746302351 | 25767/48724 |
| MoSQITo 1.2.1 / Python | 49.9075676435 | 0.816082802548 | 0.480303295409 | 24622/48724 |
| Official C / MSVC | 49.9015909659 | 0.00494218618924 | 0.477462802498 | 25763/48720 |

## Specific-loudness detail

| Implementation | workbook N′ RMS | cell N′ RMS | cell max N′ location | cell changed N′ points (>1e−12) |
|---|---|---|---|---|
| SQAT v2.0 / Octave 8.4.0 | 2.74065371887e-05 | 0.000312210625001 | sig14 @ 9.7920 s, 5.0 Bark | 85310/11693760 |
| MoSQITo 1.2.1 / Python | 0.000936246333573 | 0.000314565778408 | sig15 @ 9.5940 s, 5.8 Bark | 85877/11693760 |
| Official C / MSVC | 2.74090993151e-05 | 0.000312223314431 | sig14 @ 9.7920 s, 5.0 Bark | 85310/11692800 |

## Length and time-label accounting

| Implementation | extra output frames vs workbook (total) | max returned-label drift (s) | baseline routes / variants |
|---|---|---|---|
| SQAT v2.0 / Octave 8.4.0 | 8 | 0 | 25 / 2 |
| MoSQITo 1.2.1 / Python | 8 | 0.000499956661178 | 25 / 2 |
| Official C / MSVC | 4 | 0 | 25 / 2 |


## Interpretation and limits

- SQAT was run by executing its pinned, unchanged `.m` files directly in **GNU Octave 8.4.0**, not by translating them to C or Python. MATLAB R2021a readiness was **BLOCKED** by expired license (Error −10). Therefore the numerical evidence is native SQAT source under Octave; MATLAB-runtime acceptance remains unverified.
- MoSQITo used its original public stationary/time-varying APIs for signals 2–25. For signal 1, which is already 28-band levels, the native private `_main_loudness` → `_calc_slopes` route was used; no public level-input API is claimed. Its slope function rounds N to .001 sone at N≤16 and .01 at N>16 before time weighting; this original behavior is retained.
- The largest MoSQITo baseline workbook N discrepancy is stationary signal 5: .0808 sone. Changing this USL cell has **zero** effect there. SQAT/official C stationary levels skip the first .2 s after filtering; the unchanged MoSQITo public stationary API uses its own frontend and whole-record average without a skip parameter. The discrepancy is not attributed solely to either frontend or skip, and is not a USL-cell error.
- Across the time-varying signals, MoSQITo baseline maximum workbook N discrepancy is 0.0228893512431 sone; the .22 counterfactual maximum is 0.0232840920114 sone. A one-cell change does not monotonically improve every aggregate maximum because other differences and cancellation remain.
- The real same-core case is signal 6 internal frame **13677**, **6.8385 s**. Selection was preregistered as the maximum raw, unweighted C cell effect over that signal's core frames. Every engine receives the identical 21 binary64 values in `common-core.json`; no frontend or temporal weighting is involved in this table. The SQAT slope wrapper mechanically extracts the original stage body; hashes and source-line boundaries are in `sqat-freeze.json`.
- The synthetic vector has only band 5 = .35 sone/Bark. Analytically, over a local .2-Bark segment, the specific difference is **.004 sone/Bark**, and its segment area difference is **.0004 sone**. These are not whole-pattern N differences. Official C and SQAT add .0001 Bark to ZUP, so the actual 4.6-Bark coordinate is .1999 Bark into the slope and yields about .003998; MoSQITo gives .004. The whole-pattern differences are separately tabulated above.
- Same-core zero-vector and stationary signal-2 negative controls have exactly zero cell effect in all three engines. Full native signals **1–5 and 25** likewise have zero N and N′ cell effect in every engine. Sensitive signals and affected counts are recorded separately; not every input exercises this coefficient.
- Input WAV integers were converted identically using `int16 / 32768 * 2*sqrt(2)` to double Pa, 48 kHz, mono; no output-driven calibration. Signal 15 uses diffuse field, all others free field. Workbooks are the supplied official four-decimal references: their comparison measures numeric discrepancy, not an assertion that those decimals are exact physical truth.
- Workbook N′ is available for full 240-Bark stationary profiles (1–5) and one selected Bark trajectory per signal 6–13. It is **not** a full 240×time reference for signals 6–25. Full-grid N′ differences in the C-reference and cell-effect tables use freshly executed outputs on all common coordinates. All N′ units are sone/Bark.
- MoSQITo's returned timestamps use endpoint-inclusive linspace and drift from its actual `[::24][::4]` data-sample grid. The initial exact-label assertion correctly failed; the documented deviation in `alignment-deviation.md` maps source-defined sample indices to physical 2-ms times, with **no interpolation, fitted shift, or loudness-value change**. Original reported timestamps remain in raw arrays; drift and unmatched tail frames are explicit. Tail values absent from workbooks are excluded only from workbook comparisons; common-C and within-engine comparisons retain their respective common/full grids.
- Relative error uses only |reference|≥1e−4; exclusions and the location of maximum relative error are in detailed JSON. Supplementary |N reference|≥1-sone figures were registered before metrics. RMS is coordinate-weighted over each stated pool. Counts `above_1e12` and `above_1e4` mean absolute error >1e−12 and >1e−4 respectively. The 1e−4 diagnostic reflects workbook precision and is **not** a normative acceptance threshold. Raw absolute-error maxima and percentage-error maxima generally occur at different coordinates.
- Source-level Table A.9 authority remains **PENDING**; this experiment does not resolve a normative table-versus-reference-code conflict, declare all standards requirements passed, or authorize changing product coefficients. Official-C-versus-itself zero is a reference identity, not independent proof.

## Provenance, replay and delivery

[SQAT v2.0](https://github.com/ggrecow/SQAT/releases/tag/v2.0), commit `94f489c053d1366da05d5e62838c3f54ac7715c3`, main source SHA-256 `1113ab411f8a6792bd0f7c972bc45124187324222ee8f7d43d9e0765fd57bd5b`; [MoSQITo 1.2.1](https://pypi.org/project/mosqito/), copied installed source frozen in `frozen-inputs.json`; original official C SHA-256 `a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491`. Official C was freshly rebuilt for this round with MSVC `/O2 /fp:precise`; no old numeric output was reused. The original C is included unchanged in an original wrapper that exports its native slope and core stages.

Read `replay.md`, `preregistration.md`, `preregistration-supplement.md`, `alignment-deviation.md`, `per-signal-metrics.json`, `stratified-summary.json`, `common-core.json`, `sqat-freeze.json`, `builds.json`, `raw-output-hashes.json`, `execution-audit.json` and `delivery-check.md`. Intentional worker scheduling restart and fixed harness-only preparation errors are retained in logs; they are distinguished from numerical outcomes. Full third-party sources, WAV, workbooks and large arrays remain in local tmp, with hashes; none is republished in this delivery. Delivery-file integrity hashes are computed after redaction and are distinct from original source/binary/input hashes.
