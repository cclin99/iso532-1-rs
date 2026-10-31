# Plan timing analysis: when to split the repo and when to add the ZwtvStream pyclass (2026-07-18)
> 對照／Pair: [中文版](PLAN-TIMING-ANALYSIS-2026-07-18.zh-TW.md) · source: zh · synced 2026-11-01

> Premise: the three R5 review rounds were closed at commit `6f12e8c`; streaming API v1 (including the `iso532_stream_*` C ABI) is frozen.
> The architecture conclusion follows `docs/ARCH-EVAL-REPO-SPLIT-2026-07-18.md` (2 repos). This document answers "when to split" and "when to do the pyclass".

## 1. Project goals and progress inventory

The eight stages of the master plan `docs/superpowers/plans/2026-07-05-roadmap-master-plan.md` against the current state:

| Stage | Content | Status |
|---|---|---|
| R1 | calc_slopes dedup | ✅ (closed 2026-07-09) |
| R2 | zwst IsoReference | ⏸ deferred by user decision |
| R3 | C-ABI + Python (batch) | ✅ (`bb37c97`, 2026-07-11) |
| R4 | band-level parallelisation (offline) | ✅ (closed 2026-07-10, MT AVX2 52.2 ms) |
| R5 | streaming API + phon | ✅ (`3254bde` + `6f12e8c`, v1 frozen) |
| R6 | VST plug-in (64 tracks + panel) | not started; **the next major stage** |
| R7 | NEON + three-platform CI | not started (required before R6 ships a macOS build) |
| R8 | workspace split + sharpness | not started (trigger: work on a second standard begins) |

Completion of the three delivery options (against the ARCH-EVAL table):

- **Option 1 (stationary + C-ABI + py)**: ✅ complete.
- **Option 2 (time-varying + C-ABI + py)**: C-ABI ✅; **py has only batch `loudness_zwtv`; `ZwtvStream` is not yet bound as a pyclass**. This is the only gap.
- **Option 3 (time-varying + panel)**: not started; equals R6.

Key facts: the repo currently has **no git tag** and the root directory has **no workspace `Cargo.toml`** (the three crates are sibling directories). Both facts directly affect the timing judgments below.

## 2. Repo split timing: the day R6a starts, neither earlier nor later

**Conclusion: repo B (panel/VST) is opened at the moment the R6a feasibility prototype starts, and not before.**

### Why not earlier

- Opening earlier only yields an empty-shell repo. The three critical questions of R6a (host sample rate, whether the 64-track aggregation architecture lives in one process, CLAP/VST3 licensing) **determine the skeleton of repo B**. If the aggregation architecture is forced onto shared-memory IPC, the repo layout is completely different. Any scaffolding written before the answers are known is a guess.
- The engine side still has wrap-up work before the split (see the prerequisite list in §4). Splitting first would make repo B depend on a consumption surface that is not yet final.

### Why not later

- The R6a prototype is itself application-layer code (hooks into nih-plug, runs real DAW tests). Writing it inside the engine repo violates the isolation reasons of ARCH-EVAL (dependency weight, CI pollution, licence isolation). **The first line of prototype code should land in repo B.** So "open repo B" and "start R6a" are the same event.

### Three engine-repo prerequisites before the split (fixed order)

1. **Root workspace `Cargo.toml`** (ARCH-EVAL to-do): a purely mechanical change, unifying `cargo test --workspace`. Gate: all tests green + hash 12/12 unchanged + clippy/fmt clean. Note that the renamed dep `iso532_core` in `iso532-py` and the crate-type of the ffi are unaffected by the workspace, but profile merging must be checked (a workspace only honours the root profile; the existing `[profile.*]` settings of the three crates must be lifted to the root).
2. **ZwtvStream pyclass** (see §3): the last piece of the engine API surface.
3. **Cut the first tag** (suggested `v0.1.0`, marked ABI v1): repo B's consumption contract is "a tagged release of repo A"; without a tag there is no frozen point to depend on. Tag contents = crate (git tag dep for nih-plug) + `iso532.h` + dll/lib + wheel.

> Clarifying an easily confused point: **the "workspace split" of R8 and the root workspace here are two different things.** Prerequisite 1 only gathers the three existing sibling crates into one virtual workspace (half a day). R8 is extracting `dsp-core` out of `iso532` for reuse by sharpness/ECMA (a structural move); its trigger stays as the master plan says, "do it when the second standard starts, not earlier", and it is unrelated to the repo split.

## 3. ZwtvStream pyclass timing: now, before the repo split

**Conclusion: schedule it immediately as the next Codex round and finish it before the tag.** Reasons by weight:

1. **Completes the delivery matrix of option 2.** Having all three options available at the same time is the goal set by the user; this is the only remaining cell, and it is purely additive (the py API is not part of the v1 frozen surface).
2. **Tag completeness.** The first tag is the consumption baseline of repo B and the "full delivery point" of the three options. If the pyclass came after the tag, option 2 would only be complete at the second tag. The work is 1–2 days and blocks nothing.
3. **Context freshness.** The R5 test infrastructure (chunk invariance, ZeroState reference, pure-integer cross-language signal convention) and the memory of the three review rounds are still warm; verification cost is lowest now. Coming back to it during R6 would require re-warming.
4. **Reverse benefit**: a py streaming interface lets any engine regression during R6 be reproduced quickly from Python with pytest (one more layer of verification leverage; the same logic that put R3 before R5).

The VST itself **does not need** the pyclass (nih-plug consumes the Rust crate directly), so this is not an R6 dependency. It is a delivery item of option 2 and a matter of tag completeness.

### pyclass design points (for the phase plan to expand; direction locked here)

- **Interface**: `class ZwtvStream(field_type: str = "free")`, methods `push(chunk: np.ndarray) -> (n, n_phon, t_frame_index, flags)` (four ndarrays, length = number of frames output by that call), `flush()` returning the same shape, `reset()`, attribute `residual_flags`, `latency_samples` (class attribute / staticmethod).
- **GIL**: `push` uses `py.allow_threads`; the input is first copied into an owned buffer, following the batch convention (soundness: other threads may mutate the ndarray). **No promise of zero allocation at the py layer**: each push preallocates the output Vec with `max_frames_for_chunk` and converts to numpy. Zero allocation is a contract of the Rust hot path; the py layer already allocates ndarrays. The documentation states this.
- **Thread safety**: the handle has no internal lock; mark the pyclass `unsendable` (simplest and honest) and document single-thread use.
- **NaN/Inf semantics**: identical to the Rust stream (zero + flag, no raise). **Deliberately different from the raise behaviour of the batch py API**; the docstring states the difference and the provisional semantics of `residual_flags` before flush (reusing the text finalised in 6f12e8c).
- **Semantics after flush**: on the Rust side only reset/drop is legal after flush; the pyclass must turn a push after flush into a Python exception rather than let the internal assert become a panic. The binding layer checks a state flag first.
- **Tests**: (a) py stream vs py batch (atol 1e-9 after skipping N_WARMUP=580, restating E3); (b) py stream vs the reference hashes frozen by the Rust tests, or bitwise on pure-integer signals (following the R3 convention, no sin synthesis); (c) py version of chunk-size invariance (480 vs the whole signal in one push, bitwise); (d) NaN zeroed + flags surface, push after flush raises, after reset bitwise equal to a fresh instance.
- **The frozen surface does not move**: the C ABI, the `iso532/src` core and hash gate 12/12 must show no diff. This round touches `iso532-py/` only.

## 4. Suggested schedule (combined)

```
現在 ──► ① root workspace Cargo.toml（0.5 天，純機械，單獨 commit）
     ──► ② ZwtvStream pyclass（1–2 天，Codex，phase 計畫另出）
     ──► ③ tag v0.1.0（ABI v1；三方案全量交付點）
     ──► ④ 開 repo B ＝ R6a 可行性原型開工（三個致命問題）
              │
              ├─ R6a 期間背景調研已可開始（主計畫 §10-3 原建議）
              └─ R7（NEON + CI）與 R6a/R6b 無依賴，可插隊；
                 唯一硬約束：VST 出 macOS 版前必須完成
R2  ⏸ 維持遞延（使用者決定）
R8  ⏸ 維持「第二個標準動工才 workspace 化」，與上述皆無關
```

The order ①→②→③ cannot be swapped: ① lets the CI/tests of ② run once under the workspace to verify the move is harmless; ③ must include ② to be a complete delivery point; ④ depends on the tag of ③ as its consumption contract.

## 5. Risk memo

| # | Risk | Mitigation |
|---|---|---|
| 1 | The workspace change mixes in a behaviour change; golden failures cannot be attributed | Follow the R8 iron rule: zero logic changes, separate commit, continue only when hash 12/12 is green |
| 2 | The pyclass exposes an internal Rust assert (push after flush) as panic→abort | The binding-layer state flag blocks it first and converts it to a Python exception; panic injection test follows the R3 convention |
| 3 | The py streaming tests mistakenly use sin-synthesised signals → numpy/Rust libm ULP differences make bitwise tests falsely red | Follow the R3 decision: pure-integer arithmetic signals + constants frozen from a Rust dump |
| 4 | The tag is cut too early (before the pyclass) → the option 2 gap rolls into R6 and is forgotten | The order ①→②→③ in §4 of this document is fixed |
| 5 | The R6a prototype is written into the engine repo by mistake | Repo B is opened on the R6a start day; prototype code always lands in repo B |
