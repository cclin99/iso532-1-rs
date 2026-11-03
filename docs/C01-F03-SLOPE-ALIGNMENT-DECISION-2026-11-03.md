# Aligning the slope stage with Annex A: decision on the C-01 tail root cause and the F-03 coefficient

> Pair／對照: [繁體中文](C01-F03-SLOPE-ALIGNMENT-DECISION-2026-11-03.zh-TW.md) · source: zh · synced 2026-11-03

2026-11-03 (Asia/Taipei). Code snapshot `aa379db` (v0.3.1). Decision memo; no code or golden change. Evidence: Astra's [`verification/2026-11-03-C01-zero-pad-aa379db/`](verification/2026-11-03-C01-zero-pad-aa379db/), [`verification/2026-11-03-C01-tail-root-cause-aa379db/`](verification/2026-11-03-C01-tail-root-cause-aa379db/), [`verification/2026-11-03-F03-coefficient-hypothesis-aa379db/`](verification/2026-11-03-F03-coefficient-hypothesis-aa379db/), and Claude's cross-analysis [`verification/2026-11-03-C01-cross-analysis-aa379db/`](verification/2026-11-03-C01-cross-analysis-aa379db/).

## 0. One-line conclusion

Every difference between Rust and the official Annex A C program on identical input has been traced to four sources; three of them are deviations inherited bitwise from MoSQITo 1.2.1. Decisions: the correctness reference becomes Annex A; fix the per-frame rounding (F-04) and the dropped last-cell remainder (F-05); keep `USL[12][4] = 0.24` provisionally; generate goldens from the official C with a 1e-10 threshold; version 0.4.0.

## 1. Background

The four trailing points of C-01 (Annex B signals 18/23/24/25) had no official reference value. Astra produced one from the official C on zero-padded input: all 960 specific values agree within 1e-14, but the four totals differ by 2.0e-7 to 4.2e-7 sone, so the strict gate failed (PARTIAL). Astra's second round decomposed the tail difference by ordered stage substitution: removing Rust's per-frame rounding explains 67–98 %, the rest was attributed to the slope and main stages without further isolation. Claude's cross-analysis reproduced every Astra number independently (own TW implementation, 1 ulp) and closed both unresolved residuals.

## 2. Sources of difference (same input, same upstream history)

| # | Source | Origin | Tail effect | Whole-series weighted output (four signals) | Evidence |
|---|---|---|---|---|---|
| F-04 | Per-frame total rounded to 0.001 (N≤16) or 0.01 sone, `calc_slopes.rs:161-165`; absent in C | MoSQITo `_calc_slopes.py:350-352` | Dominant, 67–98 %; mechanism: during decay raw N < 0.0005 rounds to 0 and the 70 ms branch carries the deficit to the tail | ≤1.0e-3 sone | tail-root-cause T1; cross-analysis timeline |
| F-03 | `USL[12][4]`: Rust/MoSQITo/SQAT 0.24, C 0.22; the only differing table cell | Authority pending | ~1e-8; zero for signal 25 | **≤3.5e-3 sone, dominant over the whole series** | tail-root-cause cell counterfactual; cross-analysis table diff |
| F-05 | When a slope segment starts at the band's last 0.1-Bark grid point and reaches the core loudness before ZUP, the flat remainder up to ZUP is never integrated; the next band back-fills it | MoSQITo vectorised algorithm, bitwise identical in Rust | 6e-10 to 8e-9 (Astra's unresolved residual) | ≤1.4e-3 sone; about 1 % of frames per signal, 1e-3 to 2.6e-2 sone per frame | cross-analysis `sliver_check.py`: all 40/63/38/31 sparse frames match, no false positive; restored port vs C ≤1.4e-14 per frame, tail ≤2e-17 |
| C-f32 | The C program's own float32 constants: `_ZUP += .0001f`, ZUP/RNS/USL tables, main-stage `.0635f`/`0.4f`/`0.32f`/A0/DCB | Official C | ~1e-11 | ≤7e-8 per frame | cross-analysis `dense_check.py`, `main_check.py` (main stage closed to ≤4.4e-16) |

Incidental finding: the public `core::calc_slopes` wraps band 0 around to band 20 (`prev_grid_index(0) = 239`) when nm[20] > nm[0], producing negative specific loudness and an inflated total. Unreachable through the pipeline (both C and Rust main loudness fix nm[20] = 0; end-to-end 12.5 kHz tone and >8 kHz noise differ by ≤4e-4), so it is an API-robustness hazard recorded as hardening item F-06.

## 3. Decisions

**D1. Correctness reference = the ISO 532-1:2017 Annex A C program.** MoSQITo itself cites Annex A; where they diverge MoSQITo has no authority. README line 281 ("MoSQITo 1.2.1 is the project's primary independent implementation baseline") is reworded to "Annex A is the correctness reference; MoSQITo is the compatibility and diagnostic baseline". F-01 and F-02 are precedents of the same principle.

**D2. Fix F-04 and F-05 in `calc_slopes_impl` itself.** Both are independent of the coefficient choice (closure to arithmetic noise holds with 0.24). Stream and batch call the same function and change together; the bitwise n_only-vs-into test stays.

**D3. Keep `USL[12][4] = 0.24` provisionally,** following the SQAT and MoSQITo parameter lineage. Astra's F-03 report shows the available data cannot decide 0.22 vs 0.24 and the ISO Table A.9 cell remains PENDING. If the text later confirms 0.22, changing the cell is another numeric change requiring a minor release and golden regeneration.

**D4. Goldens generated from the official C.** The reference program is the official C with the single documented substitution `USL[12][4]` 0.22f→0.24f; both hashes are listed. Threshold 1e-10 sone (above the C float32 residue of 3–6e-11, below the three defects). The delta against the unmodified C is kept on record (tails 1e-8 to 1e-7, whole series ≤3.5e-3 sone). The MoSQITo golden becomes a tolerance comparison (≤5e-3 sone), no longer acceptance.

**D5. Version 0.4.0.** Numeric change; refreeze zwtv/zwst hashes; Annex B conformance tests expected unchanged; batch = stream gate kept.

## 4. What does not change

- API, output-grid contract (C-01 ceil decision), stream contract, SIMD dispatch, C ABI, Python shapes.
- Annex B tolerance (5 % or 0.1 sone) never resolved these three items; conformance verdicts are unchanged.
- MoSQITo remains the source of the architecture and API, the performance comparison, a legitimate stationary front end, and a compatibility mode (the F-02 `NlInit::MosqitoTail` pattern).

## 5. Risks and open items

- The Table A.9 text is still not obtained; D3 is provisional.
- Generating the C golden needs the locally preserved official C and MSVC, which are not in git; the tool must accept external material and record hashes like `tools/gen_golden.py`.
- After F-05, Rust vs C (epsilon = 0, binary64 tables) agrees to ≤1.4e-14 per frame, but ~1e-11 of C-f32 remains against the unmodified C; float32 promotion is deliberately not emulated, which is why D4 sets 1e-10.

## 6. Execution

Phase plan: [`superpowers/plans/phases/phase-0.4.0-slope-annexa.md`](superpowers/plans/phases/phase-0.4.0-slope-annexa.md), handed to the implementer (Claude Opus 5.5); Astra performs the independent acceptance afterwards.
