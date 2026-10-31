# ISO 532-1 Rust + AVX2 design development document
> 對照／Pair: [中文版](DESIGN-DEVELOPMENT-2026-07-04.zh-TW.md) · source: zh · synced 2026-11-01

**Date:** 2026-07-04
**Baseline version:** commit `ad83515` + working-copy architecture optimisation (ZwtvProcessor / rayon / calc_slopes split, not yet committed)
**Measurement environment:** AMD Ryzen 5 3600 (6 cores 12 threads, AVX2+FMA, no AVX-512), Windows 10, rustc release profile. Python control group: mosqito 1.2.1 + numpy, same machine.
**Principle:** every number in this document is measured on this machine; there are no estimated values. Where analysis extrapolates, it is marked explicitly as "estimate".

---

## 1. Purpose and scope

This document reviews the `iso532` crate after the second round of architecture optimisation (`ZwtvProcessor` scratch reuse, `calc_slopes` N-only/into split, spec down-sampling to every 4th frame, rayon frame parallelism, tol transpose) has landed, with respect to:

1. Quantisation error (against mosqito golden data, AVX vs scalar)
2. Performance gain over Python
3. Rust+AVX2+FMA speed-up factor
4. Maximum potential ceiling of further optimisation
5. Current design state for long-running stability
6. List of hidden stability defects and countermeasures
7. Architectural readiness for connecting other loudness / psychoacoustic standards in the future

Verification status: 31 tests + 2 doctests all green (including golden end-to-end, simd_parity, annexb); `cargo clippy --all-targets -- -D warnings` and `cargo fmt --check` clean.

---

## 2. Summary of the current architecture

```
signal (48 kHz f64)
  └─ third_octave_levels        28 頻帶 IIR 濾波器組，AVX2: 7×f64x4，逐樣本推進，DEC_FACTOR=24 → 2 kHz 幀網格   [序列]
  └─ 轉置 tol → frame-major     28 筆連續讀取取代 28 次跨步 gather                                              [序列]
  └─ main_loudness_frames_into  每幀 28→21 帶核心響度，rayon par_chunks_exact(28)                              [幀平行]
  └─ nl_loudness                21 帶 × 24 虛擬子步非線性衰減遞迴，AVX2: 5×f64x4 + 1 帶 scalar                  [序列·時間遞迴]
  └─ calc_slopes_n_only         每幀總響度 N（不物化 240 點 spec），rayon par_iter_mut                          [幀平行]
  └─ calc_slopes_into           僅 t%4==0 幀物化 240 點 specific loudness，rayon par_chunks_mut                 [幀平行]
  └─ temporal_weighting         0.47·LP(3.5ms) + 0.53·LP(70ms) 時間遞迴                                        [序列·時間遞迴]
  └─ 每 4 幀降採樣 → 2 ms 輸出網格（N、N_specific、time_axis）
```

`ZwtvProcessor` holds 4 scratch buffers (tol transpose, core, loudness, spec_time_major); repeated calls perform zero reallocation (there is a capacity-conservation test). The free function `loudness_zwtv()` is a one-shot wrapper. The output stays flat row-major `Vec<f64>` (preparing for the C-ABI).

---

## 3. Quantisation error (measured 2026-07-04, 9 golden datasets)

Everything was re-measured after the architecture optimisation (`calc_slopes` was refactored, so old numbers are not reused). The results are identical to those before the optimisation: the refactor changed no numerical semantics.

### 3.1 Against mosqito golden data (AVX2 path, end-to-end)

| Item | Max absolute error | Max relative error | Notes |
|---|---|---|---|
| zwst total loudness N | **0 (exactly equal)** | 0 | 9/9 datasets; mosqito rounds N to 3 decimals, and both sides agree bit for bit after rounding |
| zwst N_specific (240 points) | 8.2e-14 | 2.9e-12 | worst: sine_250_80 |
| zwtv N(t) | 1.6e-14 | 3.8e-15 | worst: annexb_sig5 |
| zwtv N_specific(t) | 1.3e-9 | 3.0e-9 | worst: step_60_80 (level step, lands on the r8 rounding boundary in calc_slopes) |

### 3.2 AVX2 vs scalar (same input, end-to-end)

| Item | Max absolute error | Max relative error |
|---|---|---|
| zwtv N(t) | **0 (9/9 bit-identical)** | 0 |
| zwtv N_specific(t) | 1.4e-9 | 3.2e-9 |

Why N(t) is bit-identical: total loudness is quantised to 1/1000 sone at the end of calc_slopes (for ≤16 sone), which absorbs the ULP-level differences caused by FMA fusion. N_specific has no such quantisation; the 1e-9-level differences come from different branch selection of step signals at the `r8()` (1e-8 rounding) boundary. This is expected, and the golden tests guard the upper bound.

### 3.3 Conclusion

All errors are at perceptually meaningless magnitudes (sone display resolution is 1e-3). The two-fold correctness guarantee of the design, (1) golden end-to-end tests locking the deviation from mosqito and (2) simd_parity tests locking the deviation of AVX from scalar, holds in full after this round of refactoring.

---

## 4. Performance: gain over Python and speed-up factor (measured)

### 4.1 criterion benchmarks (10 s three-sine signal, 480k samples)

| Benchmark | scalar | AVX2 | AVX2 speed-up |
|---|---|---|---|
| filter_bank_10s (single thread, no rayon involved) | 241.4 ms | 20.1 ms | **12.0×** |
| zwtv_10s full pipeline (rayon default 12 threads) | 397.9 ms | **79.1 ms** | **5.03×** |
| zwtv_10s full pipeline (RAYON_NUM_THREADS=1) | 598.8 ms | 285.9 ms | 2.09× |

(The 77.6 ms / 388.6 ms that Codex recorded in README/`docs/bench-results.txt` are from another run on the same day; the difference is within run-to-run noise.)

### 4.2 Optimisation trajectory (zwtv AVX2, 10 s signal)

| Milestone | Time | Relative to previous round |
|---|---|---|
| Phase 5 initial version | 387.6 ms | — |
| + nl target_feature / tail-band fix (`ad83515`) | 258.8 ms | -33% |
| + this round of architecture optimisation (multi-threaded) | **79.1 ms** | -69% |
| Cumulative | | **4.9×** |

### 4.3 Against Python (mosqito 1.2.1, measured on the same machine: 22.365 s for a 10 s signal)

| Mode | Rust time | Speed-up over Python | Real-time factor |
|---|---|---|---|
| Multi-threaded (12 threads) | 79.1 ms | **283×** | 126× |
| Single-threaded | 285.9 ms | 78× | 35× |

The Python side does not reach even half of real time (0.45× real time); the Rust side has 35× real-time headroom on a single thread.

### 4.4 Real-time budget and multi-track scaling (using single-thread numbers, one core per track)

- Amortised cost per 2 ms output frame: 285.9 ms ÷ 5000 frames = **57.2 µs/frame** → inside the 200 µs budget with **3.5×** headroom
- One core can carry 2000 ÷ 57.2 ≈ **35 tracks**; 6 physical cores theoretically ~210 tracks, in practice **~147 tracks** keeping 30% headroom
- The 64-track VST target uses only about **30%** of this machine's compute

Note: the single-thread 285.9 ms is slightly worse (+10%) than the 258.8 ms of the previous round; the cause is §5.2 item 1, a known and fixable trade-off.

---

## 5. Stage profiling and the maximum potential ceiling

### 5.1 Measured per stage (10 s signal, AVX2 path, median of 3)

| Stage | Single thread | 12 threads | Parallel gain | Property |
|---|---|---|---|---|
| filter_bank | 19.6 ms | 19.6 ms | 1× (not parallelised) | sequential scan; bands independent |
| tol transpose | 1.0 ms | 1.0 ms | — | memory movement |
| main_loudness | 48.5 ms | 8.8 ms | 5.5× | frames independent |
| nl_loudness | 17.4 ms | 17.5 ms | 1× (not parallelised) | time recursion; **bands independent** |
| calc_slopes N-only (all frames) | 148.5 ms | 16.0 ms | 9.3× | frames independent |
| calc_slopes spec (every 4th frame) | 38.6 ms | 4.9 ms | 7.9× | frames independent |
| temporal_weighting | 1.8 ms | 1.9 ms | — | time recursion |
| **Total** | **275.4 ms** | **69.7 ms** | 4.0× | criterion including allocation/assembly is 285.9/79.1 |

Under multi-threading the bottleneck has shifted completely: **all frame-parallel stages have been flattened, and the two remaining non-parallelised sequential stages, filter_bank (25%) and nl_loudness (22%), take nearly half together**, forming the current Amdahl floor (about 40 ms).

### 5.2 Remaining optimisation room (ordered by expected gain; marked as estimates, to be measured after landing)

1. **Eliminate duplicate calc_slopes computation (single thread −37 ms, estimate)**: currently `calc_slopes_n_only` runs on all frames and `calc_slopes_into` recomputes the t%4==0 frames, so 1 frame in 4 is computed twice. `calc_slopes_into` itself returns N; let t%4==0 frames take only the into path and the rest the n_only path. Single thread should return to under ~250 ms, multi-threaded saves ~4 ms. Zero numerical risk.
2. **Band-parallel filter_bank (multi-threaded 19.6→~4 ms, estimate)**: the 7 f64x4 vector groups are mutually independent and each scans the signal once in full; split into 7 rayon jobs. Each group reads the 3.84 MB signal, shareable within L3 (32 MB). Time recursion exists only "within one band"; there is no cross-band dependency; zero semantic risk.
3. **Band-group-parallel nl_loudness (multi-threaded 17.4→~4 ms, estimate)**: likewise, the 5 four-band groups + 1 scalar tail band are mutually independent; split into 6 rayon jobs. Time recursion is within a band; no cross-band dependency.
4. After landing 1–3 the multi-threaded floor is estimated at ~**25–30 ms** (10 s signal) ≈ **330–400× real time**. Beyond that the ceiling is set by memory bandwidth and by the per-sub-step recursion on the 2 kHz grid that cannot be eliminated (24 sub-steps × 20k frames); further squeezing needs a different algorithm or a wider platform vector (AVX-512 f64x8 on Zen 4+ could double the filter bank and nl again; Apple M series NEON f64x2, see ROADMAP §5).
5. **The per-frame cost in streaming mode** differs from batch amortisation: in streaming, rayon does not participate (a single frame has no parallel room), so the effective cost is the single-thread 57.2 µs/frame, estimated ~50 µs after landing item 1. Real 64-track VST throughput relies on "inter-track parallelism" (one core per track), not intra-frame parallelism, which is why all multi-track arithmetic in this document uses single-thread numbers.

---

## 6. Current design state for long-running stability

Reviewing the existing design for "continuous operation for hours to days" (VST scenario), first the parts that already stand:

1. **All recursions are contractive maps**: the biquad poles of the filter bank are inside the unit circle; the three-stage smoothing and temporal weighting have `a1 = exp(-1/(fs·τ)) < 1`; the nl network coefficients `b[4], b[5] = exp(-Δt/τ) < 1`. State is bounded and forgets initial values exponentially; there is no path for unbounded accumulation or drift.
2. **No accumulating time variables**: `time_axis` is derived from the frame index (`i·24/48000`), not from an accumulated floating-point timestamp, so there is no precision decay in long runs.
3. **Persistent objects with zero reallocation**: the `ZwtvProcessor` scratch capacity conservation is guarded by a test; repeated calls do not grow memory (nl and temporal_weighting still allocate per call internally, see §7-P1).
4. **rayon parallelism is deterministic**: all three par loops are either "each work item writes to a disjoint slot" or "order-preserving collect", with no dependency on reduction order; the same input always gives the same output (confirmed in this round: repeated Processor calls and the free function are bit-identical, and N(t) is bit-identical across AVX runs).
5. **Only one piece of global mutable state**: `FORCE_SCALAR` (AtomicBool, for tests/benchmarks only), which does not affect correctness, only path selection.

---

## 7. List of hidden stability defects and countermeasures

Graded by "must be handled before entering real-time/streaming scenarios". **Under the current batch offline use none of these is an error** (all tests green, errors within target); they are latent issues that surface when switching to long-running real-time operation.

### P0 — must be resolved before the streaming API lands

| # | Defect | Mechanism | Countermeasure |
|---|---|---|---|
| 1 | **Denormal stall** | On silent input, the smoothing filter and nl state decay exponentially into the f64 denormal range; on x86 denormal arithmetic needs microcode assistance and a single operation can be tens of times slower. `TINY=1e-12` is added only at the log10 output; the filter state itself is unprotected. Offline = slower; real time = **missed deadline**. | Set MXCSR FTZ/DAZ in kernel scope (AVX path), or flush state (`|state| < 1e-30 → 0`). The scalar path uses state flushing. Add a regression test "throughput does not degrade on long silence". |
| 2 | **No input guard for NaN/Inf** | A single NaN sample permanently poisons the state through the IIR recursion. A batch call contaminates one result and ends; in streaming the state **never recovers**. | Check each chunk at the streaming entry (an `is_finite` scan costs far less than the filtering itself); on a non-finite value, zero that sample and count/report it, or reset the state. The batch API stays as is (documented as GIGO). |
| 3 | **Non-causal initialisation and lookahead** | (a) The nl initial state reads "the final virtual sub-step of the last frame" (wraparound, replicating mosqito); (b) the sub-step interpolation of nl and temporal_weighting reads `loudness[t+1]`, a one-frame lookahead. In streaming neither the future nor the end is visible. | The design decision must be made explicit: the lookahead becomes a fixed **1-frame (0.5 ms) algorithmic delay**; the wraparound initialisation becomes zero-state initialisation (affects only the warm-up segment at the start; the difference from the golden data is confined to the first few frames; acceptance criteria must be defined and streaming-specific golden data added). |
| 4 | **Mid-stream error abort semantics** | `main_loudness` returns Err as soon as any frame has a low band >120 dB, and `collect::<Result>` makes **the whole batch fail**. In a real-time scenario one clipped frame must not kill the meter. | The streaming API switches to a per-frame policy: clamp to 120 dB and mark a flag in the result; do not abort. The batch API keeps the ISO-compliant hard error. |

### P1 — affects real-time quality; handle together with the streaming refactor

| # | Defect | Mechanism | Countermeasure |
|---|---|---|---|
| 5 | **Residual allocations on the hot path** | `nl_loudness` allocates the output Vec per call; the scalar band helper allocates 3 vectors of `24·n_time` per band (about 11.5 MB transient for a 10 s signal); `temporal_weighting` allocates 2 Vecs. Allocation is forbidden on the audio thread. | Move into the `ZwtvProcessor` scratch; the streaming version preallocates by chunk size. |
| 6 | **rayon global thread pool** | The library implicitly starts a thread pool; in a VST host the audio thread must not trigger thread creation, and multiple instances sharing the pool couple their throughput. | The streaming path naturally avoids par loops (a single frame has no parallel room); this must be guaranteed by API design. The offline path may accept an injected `ThreadPool`. |
| 7 | **panic as internal contract** | Shape asserts are safe inside Rust, but a panic crossing the C-ABI is UB; a panic in a rayon work item propagates and aborts the whole call. | The FFI layer wraps everything in `catch_unwind` and maps to error codes (ROADMAP §4 already reserves `Iso532Error`→error code). |

### P2 — known and accepted, on record

| # | Item | Explanation |
|---|---|---|
| 8 | `r8()` 1e-8 rounding + RNS linear scan | Faithful replication of mosqito branch semantics (the price of parity); step-like signals produce 1e-9-level N_specific deviation at rounding boundaries, with the golden upper bound guarded. The RNS scan is O(18) per frame per band and not a performance hot spot. |
| 9 | `FORCE_SCALAR` is process-global | Two users in the same process interfere with each other. Positioned as a test/benchmark tool; the documentation states it is not for product logic. |
| 10 | Batch API memory proportional to signal length | Peak working set for a 10 s signal is on the order of 100 MB (including core/nl/spec). Long recordings should be segmented or wait for the streaming API. |

---

## 8. Review of future standard integration

The current layering (`dsp/` generic DSP, `core/` ISO 532-1 specific, `zwst`/`zwtv` orchestration, `tables*` generated artifacts) is clean for extension. Item by item:

| Standard | Reusable | Needs adding | Architectural resistance |
|---|---|---|---|
| **sharpness (DIN 45692)** | Consumes `n_specific` directly (240 points fully output) | weighted integration function + `sone2phone` | None; the lowest-hanging fruit |
| **ISO 532-2 (Moore-Glasberg)** | golden verification method, error framework, output structure | FFT front end + ERB scale (a filtering path completely different from Bark) | Low; add an FFT module to `dsp/` (rustfft) |
| **ECMA-418-2 (Sottek)** | As above + part of the IIR infrastructure | hearing model filter bank, modulation analysis | Low-medium |
| **roughness / fluctuation strength** | specific loudness time series | modulation depth analysis | One interface point to note: the current zwtv materialises spec only every 4th frame (500 Hz grid); if modulation analysis needs full-rate 2 kHz spec, `calc_slopes_into` retains the full-rate capability and can be enabled by parameter at that time. **Do not remove the full-rate path.** |

Structural recommendations (timing: when the second standard starts, not now):

1. **Workspace split**: `dsp-core` / `iso532-1` / `<new standard>`, already reserved in ROADMAP §1; the current module boundaries are already cut this way, so it will be a move, not a refactor.
2. **Unified streaming trait**: design `LoudnessStream` (`push(&mut self, chunk) -> Option<Frame>`) as a standard-independent trait; zwtv is the first implementer, and later time-varying metrics (roughness etc.) reuse the same interface. The VST side only knows the trait.
3. **Keep the output structure flat row-major `Vec<f64>`**: the precondition for zero-copy C-ABI/numpy; the output of any new standard follows this convention.

---

## 9. Development route recommendation (priority order)

1. ~~**calc_slopes duplicate computation fix** (§5.2-1)~~ — **done (2026-07-09, R1)**: single-thread AVX2 279.1 → 244.7 ms (−12.3%), multi-threaded 76.5 → 69.3 ms (−9.4%), output bit-unchanged (12/12 hashes identical). Review and measurement records in `docs/superpowers/plans/phases/phase-r1-calc-slopes-dedup.md`.
2. **Streaming API refactor** (all of P0 + P1-5/6): VST prerequisite, including denormal protection, NaN protection, final 1-frame delay semantics, per-frame error policy, zero allocation. Do not touch the VST before this lands.
3. **filter_bank / nl band parallelism** (§5.2-2/3): another 2.3–2.8× offline throughput (estimate); orthogonal to the streaming work and can proceed in parallel.
4. **C-ABI + Python binding**: high verification convenience; `Iso532Error` and the flat output are ready (ROADMAP §4).
5. **zwst ISO reference filter bank mode** (§10.2): reuse the zwtv front end to press the stationary deviation from the ISO baseline from ±0.8% down to the quantisation floor; a small independent item that can be inserted at any time.
6. sharpness → other standards (order of §8).

---

## 10. Analysis of approximation to the ISO 532-1 reference values (measured 2026-07-04)

The errors in §3 above are compatibility errors "against mosqito". This section answers a different question: **where is the residual deviation of mosqito (= this crate) from the official ISO 532-1 reference values, why does it exist, and can it be corrected?** Reference data: the official Annex B test signals in `data/annexb/`, the reference CSV (240-point N′ curve) and the time-varying xlsx (N(t) reference curve + ±5% tolerance band).

### 10.1 Measured deviation (tool `iso_gap_report`, kept in the scratchpad)

| Test signal | Stages covered | Our N | ISO value | Deviation |
|---|---|---|---|---|
| Signal 1 (28 band levels given directly) | main_loudness + calc_slopes only | 83.300 | 83.296 | **+0.005%** (= output quantisation step) |
| Signal 3 (1 kHz 60 dB wav, 44.1k→48k) | zwst full pipeline | 4.052 | 4.019 | **+0.82%** |
| Signal 5 (pink noise 60 dB wav) | zwst full pipeline | 10.418 | 10.498 | **−0.76%** |
| Signal 10 (1 kHz tone burst 10 ms 70 dB) | zwtv full pipeline | N(t) max abs 2e-4 sone | official curve | **0/500 points outside the ±5% band**; N′(8.5 Bark) max abs 1e-4 |

Three conclusions:

1. **The loudness transformation stage (main_loudness + calc_slopes) is almost exact against the ISO baseline**: Signal 1 deviates by 0.005%, and the difference 83.300 vs 83.296 is exactly the 1/100 sone output quantisation step for >16 sone; the N′ curve has max abs 3e-4 (0/240 tolerance violations). The mathematics itself has no approximation deficiency.
2. **The zwtv time-varying pipeline is almost exact against the official reference curve**: max abs 2e-4 sone, mean signed error −0.00000. This is because the 28-band filter bank at the zwtv front end was ported from the coefficients of the ISO reference program (BASIC/C, Annex A).
3. **The residual deviation is concentrated entirely in the spectral front end of zwst**: the ±0.8% of Signals 3/5 comes entirely from mosqito computing third-octave band levels with a scipy Butterworth (IEC 61260-style) filter bank + decimate + whole-signal RMS, whereas the ISO reference values were produced with the standard's own reference filter bank. A band level difference of about 0.1 dB corresponds to a loudness difference of this magnitude; it lies inside the IEC 61260 class 1 tolerance mask and is a "compliant but different" implementation freedom, not a defect. Signal 3 additionally carries 44.1→48 kHz resampling ripple.

### 10.2 Feasibility of correction (verified experimentally)

Replace the zwst front end with **the already ported ISO reference filter bank** (`zwtv::third_octave_levels`, time-average the band intensities after skipping the first 0.5 s transient, then run the same transformation stage):

| Signal | mosqito path | ISO filter bank path |
|---|---|---|
| Signal 3 | 4.052 (+0.82%) | 4.020 (**+0.025%**, 1 quantisation step of 0.001 sone + resampling residue left) |
| Signal 5 | 10.418 (−0.76%) | 10.498 (**+0.000%, exact hit**) |

That is: **correction is possible and needs no new algorithm**; reusing the existing zwtv front end presses the stationary deviation from ±0.8% to the quantisation floor. Implementation recommendations:

1. Add `loudness_zwst_iso` (or a `ZwstMode::IsoReference` parameter) taking the ISO filter bank path; **keep the current mosqito path as the default** to preserve golden compatibility (the bit-level agreement verification system of §3 must not be broken).
2. Transient handling must be decided: this experiment skipped the first 0.5 s; the formal implementation should define the discard window from the filter bank settling time (longest time constant on the order of ~0.1 s) and document it.
3. The residual +0.025% for 44.1 kHz input comes from resampling quality and is secondary; if tighter agreement is required, switch to a high-order sinc resampler and re-measure.
4. Awareness of the ceiling: ISO 532-1 compliance is defined as a ±5% / 0.1 sone tolerance, not bit identity, and the official reference values themselves were produced by the reference program (single-precision BASIC era); the quantisation step (0.001 for ≤16 sone, 0.01 for >16 sone) is the approximation floor for any implementation. The current correction path has reached this floor.

---

## 11. Appendix: measurement methods

- **Error**: `err_report` (kept in the scratchpad) compares the 9 datasets in `data/golden/` end-to-end, max-abs / max-rel (rel counted only when the denominator is >1e-9).
- **Performance**: criterion `benches/loudness.rs` (sample_size 10), 10 s three-sine signal; single thread fixed with `RAYON_NUM_THREADS=1`.
- **Stage profiling**: `stage_profile` (kept in the scratchpad) copies `ZwtvProcessor::process` with `Instant` inserted per stage, median of 3.
- **Python**: mosqito 1.2.1 `loudness_zwtv`, same signal, median of 3 (measured 2026-07-02: 22.365 s).
- **ISO baseline approximation**: `iso_gap_report` (kept in the scratchpad) compares against the official reference values in `data/annexb/`; Signal 1 input levels taken from ISO 532-1 Annex B.2 (self-verified: computed N hits the ISO value 83.296 to the quantisation step, N′ curve 0/240 tolerance violations).
