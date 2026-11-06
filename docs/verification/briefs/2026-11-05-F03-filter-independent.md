# Verification brief: F-03 coefficient and ZWST filter improvement claims

> Pair: [繁體中文](2026-11-05-F03-filter-independent.zh-TW.md) · Source: zh · Synced 2026-11-05

Date: 2026-11-05 (Asia/Taipei). Independent verifier: Astra (`gpt-6-astra`). The user's “F0.3” is interpreted from the project records as F-03, the `USL[12][4]` 0.22/0.24 discrepancy. This round verifies new evidence; it does not decide a product migration.

## 1. Objective and claims

Independently recompute the claims in these three Opus 5.5 reports, distinguishing measurements, limited signal coverage, and inference:

- [F-03 workbook provenance](../2026-11-05-F03-workbook-provenance-118322f/report.en.md): official C with 0.22 agrees more closely with the Annex B workbooks than 0.24. Of 12,287 discriminating points, the claimed counts are 11,174 equal to 0.22, zero equal to 0.24, and 12,109 closer to 0.22.
- [ZWST front-end cause](../2026-11-05-zwst-root-cause-118322f/report.en.md): for four stationary WAVs, the Annex A filters and a 0.2 s time skip reduce relative total-loudness error from approximately −0.77% to +0.82% to ≤0.001%, at a fixed `2√2 Pa/FS` conversion.
- [Annex B conversion bias](../2026-11-05-annexb-bias-118322f/report.en.md): the calibration-file conversion differs from `2√2 Pa/FS`, contributing a separate approximately +0.15% loudness offset. Separate this effect from the filters.

Agreement with supplied numerical attachments is a different claim from historical proof of how the workbooks were produced. Agreement with official C is also distinct from agreement with the corrected Table A.9 text.

## 2. Frozen target and boundaries

- Fixed product snapshot: `118322f8300dc752f1d38a79db230a2db5ff2870` (`v0.4.0`). At delegation, the clean working tree was at `493fd595ef62aaded72ed57af1a75327ba14a5b0`. The verifier must establish source equivalence; a moving HEAD is not the tested snapshot.
- Preregister source/input/toolchain hashes, thresholds, sample counts, time/Bark grids, official-C frame selection, length boundaries, and negative controls before experiments. Earlier outputs are claims to test, not substitutes for fresh calculations.
- Diagnostic variants belong only in isolated experiment copies. Do not modify product sources, official tests, coefficient tables, goldens, or release records. No commit, push, tag, or release.
- Without page-level authoritative evidence for the relevant cell in corrected 2017-11 Table A.9, the authority gate remains PENDING. Numerical agreement cannot close it.

## 3. Experiment design

1. **Inputs and reference.** Re-extract original Annex B WAVs/workbooks and official C data; verify hashes, columns, units, and field type (signal 15 is diffuse). Verify the original C source and the single-cell patch.
2. **F-03.** Build 0.22 and 0.24 C variants with the same toolchain and rerun signals 2–25. Compare N pointwise, reporting all points, differing outputs, and points separated by ≥`2e-4 sone`. Account for decimal output rounding and examine threshold sensitivity. The Annex B 5% tolerance cannot select a coefficient.
3. **Specific loudness.** Recheck N′ for the four stationary signals and the workbook-provided N′ reference points for time-varying signals 6–13. Report actual coverage, maximum errors, and first anomalous coordinates. Uncovered portions remain PARTIAL.
4. **Front-end and conversion factors.** For signals 2–5, use a “MoSQITo/Annex A front end × calibration-file/2√2 conversion” matrix with fixed downstream computation. Report absolute/relative errors and improvement factors. Compare filters using identical inputs; do not attribute conversion gains to filters.
5. **Mechanism and negative controls.** Record band levels, sensitivity to 0/0.2 s time skips, and single-band substitutions. Identify limitations from excluding the decimation path in analytical responses. Include controls that bypass the disputed USL cell or spectral front end; distinguish separate processing stages from an untested claim of no interaction in final outputs.
6. **Scope of inference.** Assess separately “all error comes from the front end,” generalization beyond four signals, and historical workbook provenance. Untested generalization stays untested. This is numerical and attribution verification, not full product acceptance of a new front end.

## 4. Verdict and delivery

Give each item PASS/FAIL/PARTIAL/BLOCKED/SKIPPED/PENDING, pairing Opus's claim with fresh measurements. The 0.001% limit is a claim under test; 1e-4 sone checks workbook/CLI display precision. Neither alone establishes full ISO conformance. Preserve and investigate discrepancies without loosening thresholds or modifying reference data.

Deliver to `docs/verification/2026-11-05-F03-filter-independent-118322f/`; use a new round if it already exists. Include matched Chinese/English reports, preregistration, replay commands, independent harnesses, numerical summaries, original source/input/binary hashes, delivery checks, and a post-redaction integrity manifest. Keep original WAVs, workbooks, full official C sources, and large products in local experiment storage; record their hashes only.

Before delivery, run `python tools/redact_paths.py <folder>` and then `python tools/redact_paths.py --check <folder>`. Inspect skipped files/warnings, inventory unsupported formats and non-UTF-8 files, and inspect the delivery diff. Recompute delivery hashes after redaction, excluding the manifest itself; preserve the original meaning of input, binary, and tested-source hashes.
