# Verification brief: C-01, official C library reference for the trailing output point

> 對照／Pair: [中文版](2026-11-01-C01-zero-pad-reference.zh-TW.md) · source: zh · synced 2026-11-01

For: Astra (`gpt-6-astra`). Issued 2026-11-01 (Asia/Taipei) by the main agent on the user's decision "使用 ceil 方式" (keep ceil, best option of `docs/C01-OUTPUT-LENGTH-DECISION-2026-10-31.md` §4). Numeric acceptance round; no program change.

## 1. Question

The Rust batch and stream return `ceil(ceil(L/24)/4)` points. For Annex B signals 18, 23, 24 and 25 (`floor(L/24)` a multiple of 4, `L mod 24 > 0`) the last Rust point is internal frame `K = floor(L/24)`, which the official Annex A C library never emits because its frame count is the integer division `NumSamples / DecFactor`. These four points therefore have no official expected value today (memo §2.1). The repository has shown (memo §2.2, now `iso532/tests/output_grid.rs`) that the value of point `j` depends only on samples `≤ 96j`, so the official C library produces the identical frame `K` when the input is extended by zeros to at least `24(K+1)` samples.

Produce an independent expected value for each of the four points from the official C library on zero-padded input, and state whether the Rust value agrees at rounding level.

## 2. Scope

1. Build the archived official C program (`ISO_532-1.c`, SHA-256 `a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491`) with the same toolchain and flags as in the 2026-10-31 rounds; record compiler, version, flags and the binary hash.
2. For each of signals 18, 23, 24, 25: read the Annex B WAV, append zeros to `L_pad = 96 * (ceil(L/96) + 1)` samples, and run the official C library in time-varying mode at 48 kHz in the free field. Capture frame `K` directly from the undecimated total array and all 240 specific values; use CLI outputs separately to check the grid and serialization. See §2.1 for indexing and precision requirements.
3. Compare with the Rust value at the same point: run `loudness_zwtv` from the fixed tested snapshot on the **unpadded** signal, taking `n[frames-1]` and `n_specific[b * frames + frames-1]` (`b = 0..239`). Report the total absolute difference, each of the 240 Bark-step differences and their maximum. The acceptance target is total `≤ 1e-14` sone and maximum specific absolute difference `≤ 1e-14` sone/Bark. This round adopts the rounding-level threshold from memo §2.1; it is not a claim of IEEE bitwise equality. The Annex B tolerance `max(0.1, 0.05·|ref|)` is a fallback statement only.
4. Negative control / invariance control: compare **all** internal frames `0 ≤ k < K` between padded and unpadded C library runs. For total and specific separately, report comparison counts, bitwise mismatch counts, maximum differences and the first differing coordinate. CLI files sampled every 4 frames cannot substitute for all internal frames. Exact equality is expected; a failure prevents acceptance of the padded reference.
5. Length-boundary controls for the contract tests: for one base signal and lengths `L ∈ {4800, 4801, 4823, 4824, 4825, 4895, 4896, 4897}` record the C library frame count (`floor(L/24)`), the CLI total and specific point counts, and the Rust count, confirming the table in memo §2.

Out of scope: changing any output grid, golden or test; stationary mode; F-03.

### 2.1 Indexing, input and precision

- All indices are zero-based. Always derive `K = floor(L/24)` from the **original** length; assert `K mod 4 = 0` and `L mod 24 > 0`. The target output point is `j = K/4 = frames-1`, at `t = 24K/48000 = 96j/48000` seconds. Both CLI total and specific correspond to data row `j` (excluding headers), not row `K` of the total file.
- The specified padding length ensures that CLI total also includes `j`; report a missing row as an anomaly instead of silently omitting it. C library frame `K` is the numerical reference; rounded CLI text cannot establish agreement at the `1e-14` level.
- Use an independent harness to read the C library arrays after computation and before CLI serialization. A wrapper limited to calling and exporting values is allowed; do not change the official algorithm, constants, loop bounds or original file. Deliver the wrapper, build commands and hashes. If exports or an entry point must be adapted, deliver the complete transformation script and diff, demonstrating that computation is unchanged.
- Record WAV format, channels, original sample count, PCM decoding and pressure calibration. C and Rust must receive identical original pressure samples; padding only appends zeros, without resampling or renormalization. Preserve hashes of the original WAV, decoded samples and padded samples, with their encoding definitions.
- Preserve round-trip decimal values (at least 17 significant digits) and IEEE-754 binary64 bits for C and Rust total and all 240 specific values. Check finiteness and array shapes before computing errors; NaN / Infinity must not pass comparisons.
- Comparator negative control: perturb one finite value in a reference copy by more than the threshold, requiring the same comparator to return a non-AGREES verdict and identify the coordinate. Do not overwrite original evidence. Record this separately from the padding invariance control above.

### 2.2 Expected length boundaries

These are formula-derived expectations, **not executed results**. Fix one base signal of at least 4897 samples and its hash; each row uses its first `L` samples. Separately record measured C library and CLI counts and measured Rust `n`, `n_specific` and `time_axis` lengths; the specific element count must be `240 * frames`.

| L | C library frames | CLI total points | CLI specific points | Rust points |
|---:|---:|---:|---:|---:|
| 4800 | 200 | 50 | 50 | 50 |
| 4801 | 200 | 50 | 50 | 51 |
| 4823 | 200 | 50 | 50 | 51 |
| 4824 | 201 | 50 | 51 | 51 |
| 4825 | 201 | 50 | 51 | 51 |
| 4895 | 203 | 50 | 51 | 51 |
| 4896 | 204 | 51 | 51 | 51 |
| 4897 | 204 | 51 | 51 | 52 |

## 3. Rules of evidence

- Every number is produced by a script in the delivery folder and is reproducible from the recorded commit, the recorded C binary hash and the Annex B WAV hashes.
- Before starting, freeze the full and short commit IDs, working-tree status and tested-source hashes; do not follow a moving `main`. HEAD when this brief was revised was `d0bd38bba540f6b3f2414737c08c3c33c6a8c558`, for orientation only, not evidence of verification in this round. If the working tree contains uncommitted changes, create an isolated snapshot from the fixed commit; record added harness files separately from tested sources.
- Report the Rust point as bits (`f64::to_bits` hex) as well as decimal, so the comparison does not depend on printing precision.
- MoSQITo is not a reference for this round; divergences, if any, are written as 「發現／目前判斷」, never as "bug".
- If the C library cannot be made to emit frame `K` (for example a hidden length check), say so and stop; do not substitute another implementation's value.

## 4. Delivery

- Folder: `docs/verification/2026-11-01-C01-zero-pad-<tested commit>/` where `<tested commit>` is `git rev-parse --short HEAD` at the time of the round; never overwrite an earlier folder.
- Files: `report.md` (Traditional Chinese) and `report.en.md` (English), same structure and numbers; `results.json` (per signal: L, K, frames, C value, Rust value and bits, |diff|, max specific |diff|); the runner script; `delivery-check.md`.
- Also include in `results.json`: `L_pad`, `j`, time, all specific values and bits, both negative controls, eight measured boundary rows, finiteness / shape checks and individual gate statuses. Deliver commands, versions, build and execution logs, exit codes, source / input hash inventories, and a post-redaction `delivery-integrity.json`.
- Before handing over: `python tools/redact_paths.py <folder>` then `python tools/redact_paths.py --check <folder>`; record the output, including skipped files and warnings, in `delivery-check.md`. Only UTF-8 text files in the folder; the C binary and WAVs stay out of the repository (hashes only).
- Inventory unsupported extensions and non-UTF-8 files individually and inspect them separately; no warnings or exit code 0 does not establish coverage of every format. Review the delivery diff, including reports, scripts, commands, logs and inventories. Once log writing is complete, rerun redaction and `--check`, then generate the integrity manifest with final file hashes and an explicit self-exclusion. Any subsequent edit requires renewed checks and hashes. Original input / binary / tested-source hashes retain their original meaning; do not claim that redacted copies are bitwise identical to originals.
- Verdict vocabulary per point: AGREES (rounding level), WITHIN TOLERANCE (Annex B rule only), DIFFERS, NOT OBTAINABLE.
- Recommend closing this round's C-01 numerical acceptance only when total and specific for all four signals are AGREES and both negative controls and all eight boundaries pass. Separately report passed / failed / blocked / skipped / partial; retain gaps for missing inputs, build failures or unavailable full-precision values instead of promoting historical evidence to passed. Delivery does not automatically edit the audit closure row and does not include commit / push.

## 5. Context files

- `docs/C01-OUTPUT-LENGTH-DECISION-2026-10-31.md` (and `.zh-TW.md`): the three rules, the cases, the §2.2 measurement, the decision.
- `iso532/tests/output_grid.rs`: the contract tests that pin the count, the time axis and prefix determinism.
- `docs/修正報告2.md` §11.4 and §12.2 row C-01: the original audit finding and acceptance items.
- `docs/verification/README.md`: delivery conventions and the earlier rounds.
