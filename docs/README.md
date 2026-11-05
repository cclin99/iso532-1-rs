# Documentation index

> 對照／Pair: [中文版](README.zh-TW.md) · source: zh · synced 2026-11-01

Language rule: `docs/DOCUMENTATION-LANGUAGE-POLICY.md`. Paired documents exist as `NAME.md` (English) and `NAME.zh-TW.md` (Traditional Chinese) with identical structure and numbers. `python tools/doc_pairs.py --check` verifies the pairs; `--list` prints the live status. Dates below are the `synced` date of the pair.

## Start here

| document | what it is | en | zh |
|---|---|---|---|
| [`../README.md`](../README.md) | project README: scope, install, API, evidence, divergences | yes | [yes](../README.zh-TW.md) |
| [`ROADMAP.md`](ROADMAP.md) | phased roadmap and deferred items (R2 stationary IsoReference front end) | yes | [yes](ROADMAP.zh-TW.md) |
| [`RELEASE-CHECKLIST.md`](RELEASE-CHECKLIST.md) | steps for every release | yes | [yes](RELEASE-CHECKLIST.zh-TW.md) |
| [`GOLDEN-REGEN-SOP.md`](GOLDEN-REGEN-SOP.md) | how the MoSQITo golden data is regenerated and verified | yes | [yes](GOLDEN-REGEN-SOP.zh-TW.md) |
| [`DOCUMENTATION-LANGUAGE-POLICY.md`](DOCUMENTATION-LANGUAGE-POLICY.md) | this language policy, glossary, writing principles | yes | [yes](DOCUMENTATION-LANGUAGE-POLICY.zh-TW.md) |

## Releases

| document | content | en | zh |
|---|---|---|---|
| [`RELEASE-0.4.0-2026-11-04.md`](RELEASE-0.4.0-2026-11-04.md) | 0.4.0: slope stage follows Annex A (F-04 to F-07), Annex A C golden with tiered gates, MoSQITo goldens as compatibility checks; independent acceptance PARTIAL, no release blocker | yes | [yes](RELEASE-0.4.0-2026-11-04.zh-TW.md) |
| [`RELEASE-0.3.1-2026-11-01.md`](RELEASE-0.3.1-2026-11-01.md) | 0.3.1: C-02 non-finite input contract (code 4), C-01 output-grid contract and tests, V-01 validator; no numeric change | yes | [yes](RELEASE-0.3.1-2026-11-01.zh-TW.md) |
| [`RELEASE-0.3.0-2026-10-31.md`](RELEASE-0.3.0-2026-10-31.md) | 0.3.0: finding F-02 (zero-state nonlinear decay), gates, artifacts, open items | yes | [yes](RELEASE-0.3.0-2026-10-31.zh-TW.md) |
| [`RELEASE-0.2.0-2026-10-31.md`](RELEASE-0.2.0-2026-10-31.md) | 0.2.0: finding F-01 (low-frequency DLL row), gates, artifacts | yes | [yes](RELEASE-0.2.0-2026-10-31.zh-TW.md) |

## Findings, decisions and status (2026-10-31 audit cycle)

| id | document | status | en | zh |
|---|---|---|---|---|
| F-01 | [`F01-LOW-FREQ-DLL-ROW-FIX-2026-10-31.md`](F01-LOW-FREQ-DLL-ROW-FIX-2026-10-31.md) | fixed in 0.2.0 | yes | [yes](F01-LOW-FREQ-DLL-ROW-FIX-2026-10-31.zh-TW.md) |
| F-02 | [`F02-NL-ZERO-INIT-2026-10-31.md`](F02-NL-ZERO-INIT-2026-10-31.md) | fixed in 0.3.0 | yes | [yes](F02-NL-ZERO-INIT-2026-10-31.zh-TW.md) |
| F-03 | [`F03-USL12-4-STATUS-2026-10-31.md`](F03-USL12-4-STATUS-2026-10-31.md) | open: `USL[12][4]` 0.24 vs 0.22, Table A.9 pending; option B (lineage) briefed 2026-11-01; coefficient-hypothesis round 2026-11-03 cannot decide; provisional 0.24 kept per the slope-alignment decision | yes | [yes](F03-USL12-4-STATUS-2026-10-31.zh-TW.md) |
| V-01 | [`V01-ANNEXB-VALIDATOR-2026-10-31.md`](V01-ANNEXB-VALIDATOR-2026-10-31.md) | done (test-only), with the floating-point boundary root cause | yes | [yes](V01-ANNEXB-VALIDATOR-2026-10-31.zh-TW.md) |
| C-01 | [`C01-OUTPUT-LENGTH-DECISION-2026-10-31.md`](C01-OUTPUT-LENGTH-DECISION-2026-10-31.md) | decided 2026-11-01: keep ceil; contract frozen in docs and `tests/output_grid.rs`; zero-pad reference delivered 2026-11-03 (PARTIAL: specifics ≤1e-14, totals within tolerance); tail root cause traced, see the slope-alignment decision below | yes | [yes](C01-OUTPUT-LENGTH-DECISION-2026-10-31.zh-TW.md) |
| F-04 / F-05 / F-06 | [`C01-F03-SLOPE-ALIGNMENT-DECISION-2026-11-03.md`](C01-F03-SLOPE-ALIGNMENT-DECISION-2026-11-03.md) | decided 2026-11-03: Annex A C is the correctness reference; remove the per-frame rounding (F-04) and restore the dropped last-cell remainder (F-05) in `calc_slopes`; guard the band-0 wrap (F-06); keep `USL[12][4] = 0.24` provisionally; C-generated goldens at 1e-10; version 0.4.0 via [`phase-0.4.0-slope-annexa.md`](superpowers/plans/phases/phase-0.4.0-slope-annexa.md) | yes | [yes](C01-F03-SLOPE-ALIGNMENT-DECISION-2026-11-03.zh-TW.md) |
| C-02 | [`C02-NONFINITE-INPUT-2026-11-01.md`](C02-NONFINITE-INPUT-2026-11-01.md) | done: batch rejects NaN/Inf with code 4, stream flags | yes | [yes](C02-NONFINITE-INPUT-2026-11-01.zh-TW.md) |
| — | [`ISO-ANNEXB-NUMERICAL-ERROR-2026-07-04.md`](ISO-ANNEXB-NUMERICAL-ERROR-2026-07-04.md) | numerical residuals vs MoSQITo and Annex B (with the 2026-10-31 tolerance correction note) | yes | [yes](ISO-ANNEXB-NUMERICAL-ERROR-2026-07-04.zh-TW.md) |

## Design documents

| document | content | en | zh |
|---|---|---|---|
| [`DESIGN-DEVELOPMENT-2026-07-04.md`](DESIGN-DEVELOPMENT-2026-07-04.md) | architecture review: error quantification, performance, stability, hidden defects, extensibility | yes | [yes](DESIGN-DEVELOPMENT-2026-07-04.zh-TW.md) |
| [`SYSTEM-DESIGN-QA-2026-07-06.md`](SYSTEM-DESIGN-QA-2026-07-06.md) | system-design Q&A | yes | [yes](SYSTEM-DESIGN-QA-2026-07-06.zh-TW.md) |
| [`MOSQITO-VS-ISO-BASELINE-STRATEGY-2026-07-05.md`](MOSQITO-VS-ISO-BASELINE-STRATEGY-2026-07-05.md) | why MoSQITo goldens and ISO Annex B are kept as two separate baselines | yes | [yes](MOSQITO-VS-ISO-BASELINE-STRATEGY-2026-07-05.zh-TW.md) |
| [`ARCH-EVAL-REPO-SPLIT-2026-07-18.md`](ARCH-EVAL-REPO-SPLIT-2026-07-18.md) | engine / panel two-repository decision | yes | [yes](ARCH-EVAL-REPO-SPLIT-2026-07-18.zh-TW.md) |
| [`CI-HASH-GATE-DEBUG-2026-07-10.md`](CI-HASH-GATE-DEBUG-2026-07-10.md) | how the frozen-hash CI gate was debugged | yes | [yes](CI-HASH-GATE-DEBUG-2026-07-10.zh-TW.md) |
| [`PLAN-TIMING-ANALYSIS-2026-07-18.md`](PLAN-TIMING-ANALYSIS-2026-07-18.md) | timing analysis of the plan phases | yes | [yes](PLAN-TIMING-ANALYSIS-2026-07-18.zh-TW.md) |

## Independent verification (evidence, original language kept)

| document | content | language |
|---|---|---|
| [`verification/README.md`](verification/README.md) | index of all verification rounds, evidence archives, redaction rules, auditor briefs | en |
| [`修正報告.md`](修正報告.md) | 2026-10-31 audit, part 1 (pre-fix state, methodology) | zh |
| [`修正報告2.md`](修正報告2.md) | 2026-10-31 audit, part 2: priorities §12, F-01 re-verification §14, F-03 §15, V-01 specification §15.5 | zh |
| [`修正後獨立驗證報告.md`](修正後獨立驗證報告.md) | post-F-01 independent verification (`3dc420c`, `6aea8b3`) | zh |
| `verification/2026-10-31-F02-5450d39/` | F-02 verification: PASS within scope | zh |
| `verification/2026-10-31-F03-sensitivity-d623d32/` | F-03: tests cannot discriminate 0.22 from 0.24 | zh |
| `verification/2026-10-31-F03-authority-d623d32/` | F-03: Table A.9 confirmed corrected in 2017-11, cell unknown; 1991 paper has 0.22 | zh |
| `verification/2026-10-31-F03-SQAT-d623d32/` | F-03: SQAT carries 0.24 in all versions | zh |
| [`verification/briefs/2026-11-01-F03-B-aarae-lineage.md`](verification/briefs/2026-11-01-F03-B-aarae-lineage.md) | brief for F-03 option B | en + zh |
| [`verification/briefs/2026-11-01-C01-zero-pad-reference.md`](verification/briefs/2026-11-01-C01-zero-pad-reference.md) | brief for the C-01 official-C reference of the trailing point | en + zh |
| [`verification/briefs/2026-11-01-release-0.3.1-acceptance.md`](verification/briefs/2026-11-01-release-0.3.1-acceptance.md) | brief for the pre-tag acceptance of release commit `30e4279` | en + zh |
| [`verification/briefs/2026-11-04-release-0.4.0-acceptance.md`](verification/briefs/2026-11-04-release-0.4.0-acceptance.md) | brief for the pre-push, pre-tag acceptance of the 0.4.0 candidate `fca4ccd` | en + zh |
| [`verification/2026-11-02-release-0.3.1-30e4279/report.en.md`](verification/2026-11-02-release-0.3.1-30e4279/report.en.md) | 0.3.1 pre-tag acceptance on `30e4279`: ACCEPT, 8/8 items passed | en + zh |
| [`verification/2026-11-04-release-0.4.0-fca4ccd/report.en.md`](verification/2026-11-04-release-0.4.0-fca4ccd/report.en.md) | 0.4.0 pre-push acceptance on `fca4ccd`: PARTIAL, 7/9 items passed, no numeric or API blocker (no stream-specific output to check; commit-table omission corrected) | en + zh |
| [`verification/2026-11-05-perf-compliance-118322f/report.en.md`](verification/2026-11-05-perf-compliance-118322f/report.en.md) | 0.4.0 post-release check on `118322f` against `v0.3.1`: performance A/B (+2% single-thread batch, rest within noise), Annex B 73,116 / 73,116 points, Nmax / N5 diagnostics, artifact hashes | en + zh |
| [`verification/2026-11-03-C01-zero-pad-aa379db/report.md`](verification/2026-11-03-C01-zero-pad-aa379db/report.md) | C-01 official-C zero-pad reference on `aa379db`: PARTIAL (specifics ≤1e-14, totals within tolerance) | en + zh |
| [`verification/2026-11-03-C01-tail-root-cause-aa379db/report.en.md`](verification/2026-11-03-C01-tail-root-cause-aa379db/report.en.md) | C-01 tail root cause on `aa379db`: rounding explains 67–98 %, slope/main residuals quantified | en + zh |
| [`verification/2026-11-03-F03-coefficient-hypothesis-aa379db/report.md`](verification/2026-11-03-F03-coefficient-hypothesis-aa379db/report.md) | F-03: data cannot decide 0.22 vs 0.24; no table change | en + zh |
| [`verification/2026-11-03-C01-cross-analysis-aa379db/report.en.md`](verification/2026-11-03-C01-cross-analysis-aa379db/report.en.md) | Claude cross-analysis on `aa379db`: Astra rounds reproduced; residuals closed to F-05 (dropped last-cell remainder) and C float32 constants; band-0 wrap F-06 | en + zh |

## Historical review records (closed rounds; translation backlog P3)

One-line English summaries; the documents are in Chinese.

| document | summary |
|---|---|
| `ARCHITECTURE-PERFORMANCE-RISK-REPORT-2026-07-10.md` | architecture and performance risk report of the R4 band-parallel phase |
| `R3-REVIEW-2026-07-11.md`, `R3-FIXES-REVIEW-2026-07-11.md`, `R3-REVIEW-FIXES-IMPLEMENTATION-2026-07-11.md` | R3 (golden chain, FFI, Python) review, fix review and implementation notes |
| `R4-REVIEW-CLOSEOUT-2026-07-10.md` | R4 band-parallel close-out |
| `R5-REVIEW-FIXES-2026-07-17.md`, `R5-REVIEW-2-FIXES-2026-07-17.md`, `R5-REVIEW-3-FIXES-2026-07-18.md`, `R5-REVIEW-FIXES-IMPLEMENTATION-2026-07-17.md` | R5 stream API review rounds and fixes |
| `iso532-1-rs-code-review-remediation.md` | code-review remediation log |

## Working plans (single language, exempt)

`superpowers/plans/` holds the master plan (`2026-07-03-iso532-rust-avx.md`), the roadmap master plan and the per-phase Codex plans under `phases/` (including `phase-v01-annexb-validator.md`, executed 2026-10-31).

## Translation backlog

| priority | items | rule |
|---|---|---|
| P1 | none open after 2026-11-01 | every user-facing document is paired |
| P2 | none | design documents are paired |
| P3 | the historical review records above | English summary line only unless requested |
