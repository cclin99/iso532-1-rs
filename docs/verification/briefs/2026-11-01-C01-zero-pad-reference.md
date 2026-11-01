# Verification brief: C-01, official C library reference for the trailing output point

> 對照／Pair: [中文版](2026-11-01-C01-zero-pad-reference.zh-TW.md) · source: zh · synced 2026-11-01

For: Astra (`gpt-6-astra`). Issued 2026-11-01 (Asia/Taipei) by the main agent on the user's decision "使用 ceil 方式" (keep ceil, best option of `docs/C01-OUTPUT-LENGTH-DECISION-2026-10-31.md` §4). Numeric acceptance round; no program change.

## 1. Question

The Rust batch and stream return `ceil(ceil(L/24)/4)` points. For Annex B signals 18, 23, 24 and 25 (`floor(L/24)` a multiple of 4, `L mod 24 > 0`) the last Rust point is internal frame `K = floor(L/24)`, which the official Annex A C library never emits because its frame count is the integer division `NumSamples / DecFactor`. These four points therefore have no official expected value today (memo §2.1). The repository has shown (memo §2.2, now `iso532/tests/output_grid.rs`) that the value of point `j` depends only on samples `≤ 96j`, so the official C library produces the identical frame `K` when the input is extended by zeros to at least `24(K+1)` samples.

Produce an independent expected value for each of the four points from the official C library on zero-padded input, and state whether the Rust value agrees at rounding level.

## 2. Scope

1. Build the archived official C program (`ISO_532-1.c`, SHA-256 `a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491`) with the same toolchain and flags as in the 2026-10-31 rounds; record compiler, version, flags and the binary hash.
2. For each of signals 18, 23, 24, 25: read the Annex B WAV, append zeros so that the length is the next multiple of 96 plus 96 samples (so the C library emits frames `K` and beyond), run the C program in time-varying mode (free field as in Annex B), and read frame `K` from the specific-loudness and total-loudness outputs (`K/4`-th row of the specific file; frame `K` of the total file after the CLI's `floor` decimation, if present).
3. Compare with the Rust value at the same point: `n[frames-1]` and `n_specific[.., frames-1]` of `loudness_zwtv` on the **unpadded** signal (current `main`, commit recorded). Report the absolute difference per point and the maximum over the 240 Bark steps; the acceptance target is rounding level, i.e. the same class as the already verified points 14–17 (`≤ 1e-14` sone, memo §2.1), with the Annex B tolerance `max(0.1, 0.05·|ref|)` as the fallback statement only.
4. Negative control: show that padding with zeros does not change the earlier points of the C output either (frames `0..K-1` identical between padded and unpadded C runs), so the padded run is a valid reference and not a different signal.
5. Length-boundary controls for the contract tests: for one base signal and lengths `L ∈ {4800, 4801, 4823, 4824, 4825, 4895, 4896, 4897}` record the C library frame count (`floor(L/24)`), the CLI total and specific point counts, and the Rust count, confirming the table in memo §2.

Out of scope: changing any output grid, golden or test; stationary mode; F-03.

## 3. Rules of evidence

- Every number is produced by a script in the delivery folder and is reproducible from the recorded commit, the recorded C binary hash and the Annex B WAV hashes.
- Report the Rust point as bits (`f64::to_bits` hex) as well as decimal, so the comparison does not depend on printing precision.
- MoSQITo is not a reference for this round; divergences, if any, are written as 「發現／目前判斷」, never as "bug".
- If the C library cannot be made to emit frame `K` (for example a hidden length check), say so and stop; do not substitute another implementation's value.

## 4. Delivery

- Folder: `docs/verification/2026-11-01-C01-zero-pad-<tested commit>/` where `<tested commit>` is `git rev-parse --short HEAD` at the time of the round; never overwrite an earlier folder.
- Files: `report.md` (Traditional Chinese) and `report.en.md` (English), same structure and numbers; `results.json` (per signal: L, K, frames, C value, Rust value and bits, |diff|, max specific |diff|); the runner script; `delivery-check.md`.
- Before handing over: `python tools/redact_paths.py <folder>` then `python tools/redact_paths.py --check <folder>`; record the output, including skipped files and warnings, in `delivery-check.md`. Only UTF-8 text files in the folder; the C binary and WAVs stay out of the repository (hashes only).
- Verdict vocabulary per point: AGREES (rounding level), WITHIN TOLERANCE (Annex B rule only), DIFFERS, NOT OBTAINABLE.

## 5. Context files

- `docs/C01-OUTPUT-LENGTH-DECISION-2026-10-31.md` (and `.zh-TW.md`): the three rules, the cases, the §2.2 measurement, the decision.
- `iso532/tests/output_grid.rs`: the contract tests that pin the count, the time axis and prefix determinism.
- `docs/修正報告2.md` §11.4 and §12.2 row C-01: the original audit finding and acceptance items.
- `docs/verification/README.md`: delivery conventions and the earlier rounds.
