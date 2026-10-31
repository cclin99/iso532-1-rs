# C-01 Output-length contract: ceil vs floor, architecture comparison, three options

> 對照／Pair: [中文版](C01-OUTPUT-LENGTH-DECISION-2026-10-31.zh-TW.md) · source: zh · synced 2026-11-01

Dated 2026-10-31, revised 2026-11-01 (Asia/Taipei) after the user asked for the architectural comparison before deciding. Code snapshot `28f6a49` (v0.3.0 + V-01). Decision memo: no code or golden change. Revision note: §1 and §2 of the first version said the extra tail point was computed with a "zero lookahead" convention that could make its value differ from the C program's; the measurement in §2.2 shows the output value does not depend on that lookahead at all, so that caveat is withdrawn.

## 0. One-sentence conclusion

The Rust batch output has one more point than the official CLI's total-loudness file (unless the signal length is a multiple of 96 samples) but the same number of points as the official CLI's specific-loudness file (unless `floor(L/24)` is a multiple of 4 and L is not a multiple of 24). The difference is a single **trailing** point; start, phase and every earlier point are identical, and the extra point's value is fully determined by real input samples (bitwise identical to the value obtained when more samples follow). Architecturally, ceil is the only grid the stream path can produce; floor is a post-hoc truncation that needs the total length. Recommendation remains the best option: keep ceil, freeze the contract, obtain independent expected values for the four points without an official reference.

## 1. The three rules

Signal length L (samples at 48 kHz), official internal 2 kHz frame count `K = floor(L/24)`, remainder `r = L mod 24`.

| Stage | Rust (batch and stream) | Official C library (Annex A `ISO_532-1.c`) | Official CLI output files |
|---|---|---|---|
| Internal 2 kHz grid | `ceil(L/24)` frames, filter output sampled at sample `24k` ([third_octave_levels.rs:87-96](../iso532/src/zwtv/third_octave_levels.rs#L87-L96), `i % 24 == 0`) | `K = L/24` (integer division = floor), also sampled at sample `24k` (`pSPL += DecFactor` in `f_calc_third_octave_levels`) | as library |
| Output 2 ms grid | `ceil(ceil(L/24)/4)` points, internal indices `0, 4, 8, …` ([zwtv/mod.rs:18-22](../iso532/src/zwtv/mod.rs#L18-L22)) | no decimation, returns all K frames | total file: `floor(K/4)` points; specific file: every 4th frame from index 0, `ceil(K/4)` points (`docs/修正報告2.md` §11.4) |
| Time axis | `t_j = 2j ms` from 0 | same | same; §11.4 confirmed a 0 s offset on the common points |
| Value of frame t | depends only on samples `≤ 24t`: the nonlinear decay outputs the first inner iteration, which uses only the current frame ([nonlinear_decay.rs:102-130](../iso532/src/zwtv/nonlinear_decay.rs#L102-L130), `out0` at `k == 0`); the lookahead to the next frame only advances the filter state; temporal weighting is causal | identical: `f_nl` writes `f_nl_lp(Ui)` of the first iteration, the inner iterations only update state | as library |

Key point: all three share start, phase and per-frame values. The Rust point set contains the CLI specific set, which contains the CLI total set. The only difference is whether one extra trailing point exists.

## 2. When the extra point appears

| Case | Rust points | CLI total | CLI specific | Rust's extra point |
|---|---|---|---|---|
| `L mod 96 = 0` | `K/4` | `K/4` | `K/4` | none |
| `K mod 4 ≠ 0` (any r) | `ceil(K/4)` | `floor(K/4)` | `ceil(K/4)` | one more than total, **same as specific**; the point lies on the C internal grid and has a C specific reference |
| `K mod 4 = 0` and `r > 0` | `K/4 + 1` | `K/4` | `K/4` | one more than both; it is internal frame K, which Rust computes from real samples up to `24K` and the C library skips only because `NumSamples/DecFactor` is integer division; **no official reference of any kind** |

### 2.1 The eight affected Annex B signals

| Signal | Rust | CLI total | CLI specific | Case | Reference for the extra point |
|---|---:|---:|---:|---|---|
| 14 | 6578 | 6577 | 6578 | `K mod 4 ≠ 0` | matches C specific, max diff 4.92e-19 |
| 15 | 5769 | 5768 | 5769 | same | 8.50e-15 |
| 16 | 2055 | 2054 | 2055 | same | 3.26e-21 |
| 17 | 1455 | 1454 | 1455 | same | 2.31e-21 |
| 18 | 1084 | 1083 | 1083 | `K mod 4 = 0, r > 0` | none |
| 23 | 1276 | 1275 | 1275 | same | none |
| 24 | 1201 | 1200 | 1200 | same | none |
| 25 | 1276 | 1275 | 1275 | same | none |

The other 17 signals have lengths that are multiples of 96 and agree everywhere. Batch and stream frame counts were confirmed equal in the F-02 verification, including non-multiple-of-96 lengths (4801, 4823, 4895, 4897, 24013; 36/36).

### 2.2 Measurement 2026-11-01: the extra point is prefix-determined

Probe (Python binding of the current build, scratch script, not committed): four 48 kHz base signals (`broadband_570.wav`, Annex B signal 5 pink noise, Annex B signal 10 tone pulse, a synthetic 1 kHz 70 dB sine), each truncated to nine lengths `L = 96m + d`, `d ∈ {0, 1, 12, 23, 24, 25, 48, 72, 95}`, covering all three cases of §2. For each truncation:

| check | result (36/36) |
|---|---|
| Rust point count equals `ceil(ceil(L/24)/4)`; CLI formulas as in §2 | yes |
| stream (480-sample pushes + flush) point count equals batch | yes |
| batch on the truncated signal vs batch on the same signal zero-padded to the next multiple of 96 plus 96: first `n−1` points bitwise identical | yes |
| the last point (the extra one in the `K mod 4 = 0, r > 0` case): absolute difference truncated vs padded | 0.0 in all 36 |

So the extra point's value does not depend on what follows the signal: it is the same number the pipeline produces when more samples arrive, and the same number the official C library would produce for frame K if its loop ran one frame further. The earlier "zero lookahead" caveat was wrong about the output (the lookahead only affects filter state, §1). This also means an independent expected value for signals 18, 23, 24, 25 can be required to agree with the official C library on a padded input at rounding level (1e-14-class), not merely within the Annex B tolerance.

## 3. Architecture comparison

### 3.1 What each rule is, architecturally

The Rust pipeline is one causal state machine driven sample by sample: 28 third-octave filters → one 2 kHz frame at every 24th sample → 21-band core loudness → nonlinear decay state → slope stage → temporal-weighting state → one output point at every 4th frame. Batch and stream run the same stages in the same order; batch is the stream with the whole signal pushed at once. The ceil grid is not a decision anywhere in this machine: it is what falls out of "emit at every 96th sample, starting at sample 0, then flush the held frame".

The floor grid is a different kind of rule: "after the whole signal is known, drop the last output point if `L mod 96 ≠ 0`". It is a truncation applied to the finished result, and it needs L. No stage of the machine knows L; the stream path in particular cannot know it before `flush`, and even at `flush` it has already computed the frame it would have to drop.

The official material itself contains both conventions: the C library floors the internal frame count, the CLI total writer floors again, but the CLI specific writer uses ceil on the same internal frames. There is no single "official" tail rule to align with.

### 3.2 Impact by layer

| Layer | Keep ceil (status quo) | Switch to floor (CLI total) |
|---|---|---|
| Core pipeline (`iso532/src`) | unchanged | a length-dependent truncation after the slope stage; `zwtv_out_frames` changes; the prefix-causality property survives (floor output is a prefix of ceil output) but batch and stream now produce different counts |
| Batch API (`loudness_zwtv`, `ZwtvProcessor`) | unchanged | shape change for every `L mod 96 ≠ 0`; 0.4.0 |
| Stream API (`ZwtvStream`, panel) | unchanged; the stream can only produce ceil | either `flush` gains a total-length argument (API change, caller must know L, stops being a stream) or the stream keeps ceil and the "batch equals stream bitwise from frame 0" gate from F-02 is dropped |
| C ABI | `iso532_zwtv_out_frames` unchanged | its value changes; callers with a hand-copied formula over-allocate or read out of bounds; header note; v1 semantics change |
| Python / NumPy | unchanged; same shape as MoSQITo | shape differs from MoSQITo (MoSQITo is ceil-like, our goldens match it); parity tests must trim |
| Goldens and frozen hashes | unchanged | all zwtv hashes re-recorded; MoSQITo goldens trimmed before comparison |
| Verification harness (Annex B, official C) | one documented trimming formula to reach CLI total; the 14–17 extra points keep their verified C specific match | CLI total shape equivalent by construction, but CLI specific now has one point more than Rust for `K mod 4 ≠ 0`; the verified 14–17 points are discarded |
| Future exact-Annex-A mode (ROADMAP R2 stationary IsoReference; later a time-varying twin) | the C tail conventions can be added together as an opt-in mode if ever wanted | the grid convention changes now while every other convention stays, mixing two sources in the default path |
| Documentation and versioning | fits 0.3.x; contract documented once | 0.4.0; migration notes in three bindings |

### 3.3 Long-term consequences

- **Comparability.** With ceil, comparison to the CLI total is a one-line trim (`floor(floor(L/24)/4)` points) done by the harness; comparison to MoSQITo, SQAT and the stream is direct. With floor, comparison to the CLI total is direct, and every other comparison (MoSQITo goldens, stream, CLI specific) needs padding or trimming.
- **Invariants.** Ceil keeps two invariants that are cheap to test and valuable for a real-time product: prefix causality (`out(x[:L])[j] == out(x)[j]` for `96j < L`) and batch ≡ stream. Floor keeps the first, loses the second.
- **Extensibility.** Any future mode that wants the C tail conventions (floor grid, and the stationary `TimeSkip` front end) can be one opt-in switch on top of the unchanged default. Changing the default grid now would have to be undone or duplicated when that mode arrives.
- **Cost of being wrong.** If ceil is kept and later judged wrong, the fix is a trim that callers can already apply today. If floor is adopted and later judged wrong, the fix is a second breaking shape change.

## 4. Three options

| | Best (recommended) | Middle | Worst |
|---|---|---|---|
| Action | keep ceil; freeze the output-grid contract in docs; add contract tests; one independent round produces expected values for the extra points of 18/23/24/25 from the official C library on zero-padded input | keep ceil; docs and contract tests only; extra points permanently marked "no official reference" | switch batch to floor(floor(L/24)/4) to match CLI total |
| Numeric / shape change | none | none | shape change (one point fewer for 8 of 25 Annex B signals and for every signal with `L mod 96 ≠ 0`) |
| Batch = stream bitwise | kept | kept | lost, or `flush` needs the total length |
| Audit C-01 status | closable: the four points get an official-C expected value at rounding level (§2.2) | PARTIAL, documented | total shape equivalent, but specific and the verified 14–17 points become a different PARTIAL |
| Cost | 0.5 day docs + 0.5 day tests (Codex phase) + one Astra round | 0.5 day docs + 0.5 day tests | code + three bindings + hash re-freeze + golden trimming + 0.4.0 release + re-verification, about 2–3 days, plus downstream migration |
| Risk | low | low | medium: a breaking change that aligns with only one of the CLI's two outputs |

### 4.1 Where the independent expected values come from

The extra point (signals 18, 23, 24, 25) is internal frame K, sampled at real sample `24K`. Zero-padding the signal to at least `24(K+1)` samples and running the official C library makes it produce frame K from the identical 28 band levels; §2.2 shows the frame's value does not depend on the padding. The expected value can therefore be required to agree at rounding level (the 14–17 points agree to 1e-14 or better), and the Annex B tolerance verdict (V-01) is only the fallback statement.

### 4.2 A common alternative: an opt-in output-grid option

For example `OutputGrid::Full` (default) and `OutputGrid::CliTotal`. Not listed as a separate option because trimming is a one-liner for the caller, the stream cannot honour it, and a new API surface has to be maintained in Rust, the C ABI and Python. A documented trimming formula is cheaper.

## 5. Decisions needed

1. Best, middle or worst. Recommendation: best.
2. If best: authorise one Astra round "zero-padded official C library reference for signals 18/23/24/25" (plus the length-boundary cases of the contract tests).
3. Whether the C tail conventions go on the backlog of a future opt-in exact-Annex-A mode together with the ROADMAP R2 stationary front end.

## 6. Work needed under every option

- Write the §1 contract into both READMEs and the header comment: start 0, 2 ms phase, count formula, "value of point j depends only on samples ≤ 96j", trimming formulas for CLI total / specific.
- Contract tests: length 4800 (shortest legal), `24k±1`, `96k±1`, and stream with arbitrary chunking plus flush having the same count as batch; truncated vs padded prefix bitwise (the §2.2 probe as a test); check the lengths of `n`, `n_specific` and `time_axis` separately.
- Complete the remaining acceptance items of audit §12.2 row C-01 in the same phase (empty / very short input is already covered by `SignalTooShort`).
