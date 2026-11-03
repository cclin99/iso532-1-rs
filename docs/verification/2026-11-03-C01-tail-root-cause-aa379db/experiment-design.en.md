# C-01 tail root-cause experiment design — preregistered

2026-11-03 (Asia/Taipei). Independent verifier: Astra. Fixed commit aa379db8f3dc37f5048ac6c8b7a6d4ba2a6c3b76. Written before new computation. Pair: [Traditional Chinese](experiment-design.md).

## 1. Frozen inputs and baseline

Use Annex B 18/23/24/25 and EXACT calibrated pressure bytes inventoried below, copied read-only from the preceding scratch (mono PCM16 48 kHz, Annex C 60 dB calibration). Verify original WAV/archive hashes too. This explicitly reuses frozen inputs, not previous computed outputs as new evidence. Recompute original Rust public outputs and padded C public outputs. Require the four old total bits to reproduce exactly; any mismatch blocks interpretation pending investigation. K=floor(L/24), L_pad=96*(ceil(L/96)+1), target j=K/4. On padded identical input both full internal grids have L_pad/24 frames. All stage comparisons focus on 0..K inclusive while preserving full arrays and hashes in scratch.

|Signal|L|Pressure f64le SHA-256|C padded tail|Rust original tail|
|---|---|---|---|---|
|18|103969|b16a82ee3b9f3eeec6261da60083d4de9af6a85c373b7f96a4ae024a5d5aef7a|0.00095543263901191108|0.00095521696145359593|
|23|122401|c67d32d7146dbf2a83791ff439973642f0089a9c17e1ae133502b80827837433|0.0034913530909121875|0.0034909360388862636|
|24|115202|2f20c961bb76b3f29e8d36a3a80edddfc56336c4784bfefece75831e474d1298|0.0010659327175432183|0.0010656334112001788|
|25|122401|0f2ecae2a233732ad0763da35c20168aaa19db3af8298f88539b1faf358babcb|0.0011947790020081512|0.0011945761670982473|

Official C source SHA-256 a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491; unchanged official compilation unit, MSVC /O2 /fp:precise. Isolated Rust fixed source snapshot and separate harness; no production source/test/golden/decision/audit-row modification, no commit/push. New delivery/scratch only; all older evidence stays unchanged.

## 2. Falsifiable hypotheses and controls

H1 (priority): Rust's per-frame slope-total rounding (0.001 sone for N<=16, 0.01 above 16) contributes to the final total discrepancy. Official C slope total has only non-negative clipping. Test rounded/raw histories on the SAME upstream nonlinear frames and SAME temporal-weighting implementation. Require re-rounding raw Rust history to reproduce its rounded history bitwise; do not infer contribution from source alone.

H2: different temporal-weighting arithmetic creates the discrepancy. Feed identical C/Rust rounded/raw total histories into BOTH official C TW and Rust TW; compare full histories and target. H3: residual differences originate upstream or in slope semantics (USL cell, float constants, grids/comparisons). Measure each complete stage, same-input stage comparisons and a fixed ordered cross-pipeline decomposition. Single-cell 0.24->0.22 on Rust raw slopes is a targeted counterfactual only, not an authority/correction decision. A whole-slope swap cannot alone attribute its residual to that cell.

Before interpretation, require instrumented/replayed C pipeline to match unmodified C public API at ALL internal frames (total and 240 specific), and Rust replay to match unmodified public API at all sampled frames bitwise. The Rust baseline imports the unchanged crate's public stages. Raw and cell variants are separately generated modules from the exact slope/table source; deliver full transformation/diffs and pre/post hashes. C wrapper only calls/exports existing stages, without rewriting original calculation bodies. The main experiment stops for harness diagnosis if equivalence fails; retain failed attempts.

## 3. Locked intervention order and quantitative thresholds

Define E_i=T_i-T_C at internal target K, signed (Rust-style minus official C). The initial baseline T_0 is original Rust. Fix this order BEFORE running:

1. T_1: remove only Rust slope-total rounding; retain Rust upstream and TW.
2. T_2: replace raw Rust slopes with official C slopes, same Rust nonlinear history and Rust TW.
3. T_3: replace nonlinear decay with C on the SAME Rust core history, then C slopes/Rust TW.
4. T_4: replace main loudness with C on the SAME Rust filter/SPL history, then C nonlinear/slopes and Rust TW.
5. T_5: replace filter/SPL with C (thus the complete C pre-weighting history), retain Rust TW.
6. T_6: use C TW, reaching the unmodified official-C baseline.

Report signed contribution E_(i-1)-E_i, residual E_i, abs residual, signed fraction contribution/E_0, and telescoping reconstruction error. Negative or >100% contributions remain visible; this is an ORDER-DEPENDENT decomposition, not a unique independent-cause allocation. Also inject Rust-style rounding into the C pre-weighting history and run both TW implementations (reverse control), and compare raw Rust 0.24/0.22 cell variants. If necessary, follow residuals only far enough to distinguish algorithm semantics from floating arithmetic; no unconstrained optimization or code correction.

The previous absolute 1e-14 sone/sone-Bark acceptance threshold is unchanged. Baseline/equivalence controls require bitwise equality; finite and shape checks precede all arithmetic. For root-cause decomposition, require |sum(contributions)-E_0|<=1e-14 and final residual <=1e-14. Report whether EACH intermediate residual meets 1e-14 rather than accepting a percentage explanation alone. Retain at least 17-digit decimal strings and binary64 bits for target, first-different and worst coordinates, and raw stage/input/source/binary hashes.

## 4. Negative/positive controls and measurements

Comparator self-comparison must show zero differences. Inject +1e-6 into one finite reference-copy value at a known stage coordinate; the same finite/shape/error comparator must identify that coordinate above 1e-14. Reject nonfinite or wrong shape. For a causal propagation positive control, add +0.01 to a pre-weighting total sample 20 frames before target K and require a detectable target change >1e-14 through each TW implementation. Never alter originals. No new broad/full-suite tests are needed.

For filter/SPL (28 bands), corrected main (21), nonlinear (21), unrounded/rounded slope total, specific (240) and weighted total: report counts, earliest chronological bitwise/threshold differences, maximum difference and coordinate, target differences, plus precision values. Compare both native-input stages and same-input stages. Preserve full raw arrays in scratch; deliver compact stage/target CSVs, not binary arrays.

## 5. Decision and delivery

Classify confirmed causes, inferred mechanisms and unresolved residuals separately. A quantitative dominant cause is not automatically a complete 1e-14 solution, a normative bug ruling or permission to change code. Do not close C-01. Deliver matching bilingual design/reports, results.json, full harness/transformation diffs, stage/target CSV, commands/versions/logs/exit codes, provenance hashes, delivery-check.md and final integrity manifest. Only UTF-8 text enters delivery. Run both path-redaction passes, explicitly inventory skipped/unsupported/non-UTF8 files, inspect diffs, repeat after final text, then hash delivered bytes excluding the manifest itself. Preserve original-material hash semantics.
