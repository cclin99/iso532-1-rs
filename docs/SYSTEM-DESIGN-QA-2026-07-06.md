# System design Q&A: SIMD, precision, cache, memory, parallelisation
> 對照／Pair: [中文版](SYSTEM-DESIGN-QA-2026-07-06.zh-TW.md) · source: zh · synced 2026-11-01

**Date:** 2026-07-06
**Nature:** reference document (system analysis, seven questions and answers)
**Evidence sources:** `iso532/src/` (checked file by file), `tests/` (measured tolerances), `DESIGN-DEVELOPMENT-2026-07-04.md` §3–§7, risk register of `2026-07-05-roadmap-master-plan.md`
**Reference hardware:** Ryzen 5 3600 (Zen 2, 6C/12T, L1d 32 KB/core, L2 512 KB/core, L3 32 MB)

---

## Q1. Why can AVX+FMA achieve "multi-core continuous integration"? Where was the key difficulty broken through?

### 1.1 First correct a concept: AVX+FMA and multi-core are two independent axes

| Axis | Mechanism | Use in this project |
|---|---|---|
| **SIMD (inside one core)** | One AVX2 instruction computes 4 f64 at once; FMA fuses multiply-add into a single instruction with a single rounding | Filter bank and nl nonlinear temporal decay: **the recursive parts** |
| **Multi-core (rayon)** | Work-stealing thread pool, fork-join data parallelism | main_loudness and calc_slopes: **the frame-independent parts** |

"Continuous integration" (advancing IIR recursive state sample by sample) **was never made multi-core**. It is mathematically indivisible: the state at sample n depends on sample n−1, and any cut across cores would break the state chain. The measured profile reflects this faithfully: filter_bank (25%) and nl (22%) are single-threaded sequential segments and form the Amdahl ceiling (12 threads yield 3.6×, not 12×).

### 1.2 The real breakthrough: vectorise along a different dimension

Recursion along the **time axis** cannot be parallelised, but ISO 532-1 has 28 bands and each band is an **independent recursive system**. So vectorisation runs along the **band axis**:

- **Filter bank** (`third_octave_levels.rs:64`): 28 bands = 7 groups of f64x4. For each incoming sample, `_mm256_set1_pd` broadcasts it to all lanes, and the 7 vector groups each advance 3 biquad sections (transposed direct-form II state `z0/z1`) + 3 smoothing stages, so **one pass over the signal covers all 28 bands**. The signal streams from memory only once; the filter state stays in registers/L1 throughout.
- **nl nonlinear temporal decay** (`nonlinear_decay.rs:109`): 21 bands = 5 groups of f64x4 + 1 scalar tail band (band 20).

### 1.3 Three concrete difficulties and their solutions

1. **The time dependency cannot be cut** → the dimension change above (bands side by side); this is the pivot of the whole design.
2. **Data-dependent branches in nl**: the mosqito nl kernel is a chain of 4 if/else decisions (fast decay / slow decay / u2 update / tracking); each lane may take a different branch, and SIMD cannot let lanes diverge → rewritten in **branchless mask form**: each condition becomes an all-ones/all-zeros mask via `_mm256_cmp_pd`, and `_mm256_blendv_pd` selects per lane (`nonlinear_decay.rs:193-226`). All four paths are computed and then selected by mask. Under SIMD, "compute more without diverging" beats "compute less with divergence".
3. **FMA changes rounding**: `_mm256_fmadd_pd` rounds the multiply-add once, differing from the scalar double rounding at ULP level → not avoided; instead the **simd_parity tests** lock an upper bound (filter bank rtol 1e-10, nl rtol 1e-12, `tests/simd_parity.rs`), and the regression baseline is always the mosqito golden data (end-to-end 8.2e-14), proving that the FMA difference does not amplify.

One easily overlooked correctness detail: the nl wraparound initialisation (mosqito semantics: at col=0 read the "previous column", i.e. the last virtual sub-step) is replicated in the AVX2 version by precomputing the 23rd sub-step of the last frame into `prev_uo` (`nonlinear_decay.rs:174-178`). This is one of the preconditions for parity passing at 1e-12.

---

## Q2. Where is the 1e-12 in the tests specified? How much higher is the precision than Python?

### 2.1 Origin: no standard specifies 1e-12. It is an engineering threshold set by this project

Two tolerance systems coexist at completely different levels:

| Layer | Tolerance | Origin |
|---|---|---|
| **Compliance layer** | relative ±5% or absolute 0.1 sone | Specified explicitly in ISO 532-1 §5.1; `isoclose` in `tests/annexb.rs:7`, same criterion as mosqito's own tests |
| **Parity layer** | 1e-6 to 1e-15 per stage | **Set by this project**, hard-coded in the `assert_close(got, want, rtol, atol)` call parameters of each golden test (`tests/common/mod.rs:22`), chosen per stage as "measured maximum deviation of that stage × safety margin" |

Actual thresholds per stage (criterion `|diff| ≤ atol + rtol·|want|`):

| Stage | rtol | atol | Why this magnitude |
|---|---|---|---|
| sosfilt (DSP primitive) | 1e-12 | 1e-15 | Pure linear recursion, replicated operation by operation in the same order; differences only from instruction-scheduling rounding |
| main_loudness (nm) | 1e-9 | 1e-15 | libm implementation differences of powf/log10 (Rust vs numpy) |
| Filter bank (28 third-octave band levels) | 1e-7 | 1e-12 | Recursive accumulation over tens of thousands of samples + dB conversion |
| nl_loudness | 1e-6 | 1e-9 | The branch decision chain is sensitive to ULP-level differences (flipping at critical points); widest error bound |
| End-to-end N(t) | 1e-6 | 1e-9 | Upstream accumulation |
| SIMD vs scalar | 1e-10 / 1e-12 | 1e-12 / 1e-14 | Only FMA rounding apart, no algorithmic difference, so stricter than the comparison against Python |

### 2.2 "How much more precise than Python": the correct statement is same precision, verification density ten orders of magnitude higher

To be honest: Rust and Python (numpy) are both IEEE 754 double, and **single-operation precision is identical**. There is no "Rust computes more accurately". The actual relationship is:

- end-to-end deviation from mosqito **8.2e-14 (relative)**: this implementation agrees with the Python reference near the limit of what double can express;
- the regression thresholds of this project (1e-6 to 1e-12) are **4 to 10 orders of magnitude stricter** than the ISO compliance tolerance (5e-2). That is the real difference: mosqito verifies itself only to ±5%; we verify to the ULP neighbourhood;
- what is higher than Python is not precision but **speed (283×) and determinism** (see Q3.3: thread count does not affect the result bits).

---

## Q3. Do L1/L2 cache hits reach the hardware limit? Does single-core / multi-core sacrifice precision or performance?

### 3.1 Honest answer: not measured, so we cannot claim "at the limit"

The project has **no hardware performance counter data** so far (perf / AMD uProf L1d/L2 hit rates, IPC, memory bandwidth). What exists is wall-clock time and profile percentages. "Whether the hardware limit is reached" cannot be answered at present; only design-level reasoning can be given:

- **Filter bank**: the state (7 groups × 9 ymm vectors) exceeds the 16 physical ymm registers, so part of it spills to the stack, but the spill slots stay in L1 throughout; the signal body is read strictly sequentially, once (the friendliest pattern for the hardware prefetcher). This segment is almost certainly **compute-bound, not cache-bound**.
- **nl**: in the band-major layout each group of 4 bands does gather-style loads across 4 rows spaced `n_time×8 bytes` apart (`_mm256_set_pd`, `nonlinear_decay.rs:146`). For a 10 s signal n_time=20,000 → 160 KB per row, a 4-row working set of 640 KB **exceeds L2 (512 KB)**, but each time step touches only 8 scalars and advances sequentially, so the prefetcher keeps up; the real cost is the computation of 24 sub-steps × 4 mask chains per step.
- Judgment: currently compute-bound, not memory-bound; the cache is "sufficient" but **"at the limit" is unproven**. To prove it, measure `perf stat -e L1-dcache-load-misses,l2_cache_misses` or the uProf equivalent, segmented for filter_bank and nl. This can be scheduled as the baseline measurement before R4 (band-level parallelisation) starts; the false-sharing risk of R4 needs the same tools anyway.

### 3.2 Does multi-core sacrifice performance? No, but there is an Amdahl ceiling

12 threads 79.1 ms vs single thread 285.9 ms = 3.6×. The parallelisation is not done badly; **only the frame-independent stages were parallelised** (main_loudness, calc_slopes, N(t)), while the recursive stages (filter_bank 25% + nl 22%) are single-threaded sequential segments. The band-level parallelisation of R4 (28 bands distributed over cores, still SIMD inside each core) targets exactly this ceiling; estimate 19.6→~4 ms / 17.4→~4 ms.

### 3.3 Does multi-core sacrifice precision? Zero sacrifice, bit-level determinism, by deliberate design

The three rayon parallel points (`zwtv/mod.rs:54,64`, `main_loudness.rs:93`) are all **pure maps**: each frame reads its own input and writes its own disjoint output slice (`par_chunks_mut`); **there is no parallel reduction anywhere**. Floating-point addition is not associative, and a parallel reduction whose summation order changes with thread count would make results drift. No such point exists in this design, so:

> **With 1, 6, 12 or any number of threads the output bits are identical; the same input run ten thousand times gives identical bits.**

The test at `zwtv/mod.rs:135-139` verifies repeat-run consistency with `assert_eq!` (bit equality, not tolerance). This property is foundational for a project whose verification axis is golden parity: if results changed with thread count, 1e-12-level parity tests could not exist at all.

---

## Q4. Which effective designs were made for memory control?

1. **Scratch reuse** (`ZwtvProcessor`, `zwtv/mod.rs:12-17`): four working buffers hang on the processor struct; repeated calls only `resize` without reallocating; the test asserts that capacity is unchanged after the second call (`zwtv/mod.rs:135`). The batch API `loudness_zwtv` is its one-shot shell.
2. **Layout follows the access pattern through transposes**: the same data is deliberately transposed three times in the pipeline: filter bank output band-major (each band written sequentially) → transposed to frame-major `t*28+band` for main_loudness (28 contiguous values per frame, cache-line scale) → back to band-major for nl (each band recurses along time sequentially) → calc_slopes outputs time-major 240-chunks (one contiguous block per frame for `par_chunks_mut`, naturally avoiding false sharing) → finally transposed to bark-major for the public API. The transpose cost is an O(n) sequential copy, bought in exchange for **zero strided access** inside each computation stage.
3. **Output de-materialisation**: the 240-point specific loudness is materialised only every 4th frame (the 2 ms output grid points) (`n_out = n_time.div_ceil(4)`); intermediate frames compute only the scalar N (`calc_slopes_n_only`), saving 75% of the 240-point computation and storage. The R1 dedup (−37 ms) is the next step of the same idea.
4. **Flat row-major `Vec<f64>`**: all multi-dimensional data is one contiguous allocation (no nested Vec, no pointer chasing). This is a decision locked explicitly in the ROADMAP; it serves cache behaviour and the R3 C-ABI at the same time (FFI passes pointer + stride directly, zero copy).
5. **Registered debt (P1)**: the hot path still allocates: nl allocates `out` per call and the scalar band also allocates `ui_delta`/`uo`/`u2`; temporal_weighting allocates `fast`/`slow`; the scalar filter path copies the whole signal per band. Unnoticeable in batch mode (once per call), but R5 streaming mode must bring it to zero (a zero-allocation push path is an R5 acceptance criterion).
6. **No ring buffer in the computation layer** (conclusion of a previous analysis): the state is a struct at the level of recursive filter coefficients + 1 frame of delay + a carry buffer of <24 samples; ring buffers belong only to the VST audio→GUI SPSC channel.

---

## Q5. Are there hidden, unknown risks in scaling the system?

Yes, and most are already explicitly registered (DESIGN §7 + master plan risk register). Ordered by "only detonates on scaling":

| Risk | Trigger scenario | Status |
|---|---|---|
| **Denormal stall** | Streaming/VST hits a silent segment; recursive filter state decays into the denormal range; Zen 2 pays ~100 cycles per operation and the real-time budget blows up instantly | P0 known; R5 handles it with MXCSR FTZ/DAZ (RAII guard). **FTZ makes the streaming output differ from the batch reference at ULP level; the acceptance definition of "bit-identical" must be decided before R5 starts**, otherwise rework mid-way |
| **NaN/Inf state poisoning** | A long-lived processor receives one bad sample; the recursive state is permanently contaminated and all subsequent output is NaN with no self-healing | P0 known; R5 needs entry checks or state sentinels |
| **Coefficients baked for 48 kHz** | The VST host supplies 44.1 kHz (most sessions); currently we can only reject | Must be answered by the R6a prototype |
| **Non-causal residue** | 1-frame lookahead + nl wraparound initialisation; unnoticeable in batch, a semantic problem in streaming (R5 handles it with a 1-frame delay + `latency_samples()=24` contract) | Already in the R5 plan |
| **rayon global pool** | When loaded by a host process (DAW), the global thread pool competes with the host for cores, or multiple instances compete with each other; the same applies when the library is embedded as a lib | P1 known; the R5 "no-rayon path" is an acceptance item |
| **panic across the C-ABI = UB** | After R3, any internal assert firing is undefined behaviour | R3 handles it with `ffi_guard!` (catch_unwind → error code −2) |
| **Golden regeneration chain breaks** | Golden data depends on mosqito 1.2.1 + a specific scipy; if the environment is lost, the whole 1e-12-level verification system cannot be regenerated | X1: lock requirements + check the golden SHA256 manifest into the repo (R7) |
| **simd_parity silently skips** | On non-AVX2 machines (including future ARM CI) the parity test prints one line and returns; the green light is fake | R7 must change it to an explicit skip marker |
| **The truly "unknown" piece** | No systematic testing of pathological input: the behaviour of NaN/Inf/±huge/DC/clipped signals entering the API has never been covered by fuzz or property-based tests; input validation covers only fs, length and 120 dB | **Never registered before; added by this document.** Recommended for the R5 phase plan (the streaming entry point is the natural choke point) |

---

## Q6. How is the deadlock problem of multi-core operation solved?

**Answer: deadlock is not "solved"; the structure makes it impossible to form.**

1. **There are no locks in the whole crate.** grep proves it: no `Mutex`, no `RwLock`, no `condvar`, no channels. The only synchronisation primitive is one `AtomicBool` (`FORCE_SCALAR` at `simd/mod.rs:3`, Relaxed, a test switch). A single atomic variable has no wait semantics and cannot take part in a circular wait. Of the four deadlock conditions, "hold and wait" and "circular wait" do not exist structurally in this crate.
2. **rayon fork-join is acyclic**: `par_iter_mut`/`par_chunks_mut` hand disjoint mutable slices to the work-stealing pool; the join point is the only wait, and the wait graph is a tree, not a cycle. The Rust borrow checker guarantees **at compile time** that slices are disjoint and there is no shared mutable state; data races (the usual prelude to deadlock) are excluded by the type system, not by discipline.
3. **No nested blocking**: there is currently no pattern of "waiting for another rayon task inside a rayon task" or "blocking I/O inside a parallel region". That is the only shape under rayon that can realistically starve or quasi-deadlock; it is a code-review red line.
4. **Places where wait semantics will be introduced in the future, and the countermeasures** (deadlock risk only enters with scaling):
   - **VST audio↔GUI** (R6): the audio thread never takes a lock, the iron rule of real-time audio; the design is fixed as a wait-free SPSC ring buffer (rtrb candidate): drop frames when full, never block;
   - **Multi-instance aggregation inside the host** (R6c): if the in-process registry is lock-protected, the audio thread may only try_lock-or-skip, never wait;
   - **Multi-threaded C-ABI calls** (R3): the API is designed so that each caller holds its own handle (`ZwtvProcessor` is not `Sync`, not shared); the documentation states "one handle, one thread"; no internal lock is provided.

---

## Q7. Points not asked about, but which are system characteristics or must be considered

1. **Determinism is a product-level feature, not just an implementation detail.** Same input → bit-identical output, independent of thread count and number of reruns (Q3.3). In acoustic measurement this is a selling point (reports are reproducible and auditable), and it is the precondition for the whole 1e-12 verification system. Any future change (especially R4 band-level parallelisation) that introduces a parallel reduction would **silently destroy** this property. Recommendation: make "thread-count invariance" a permanent test rather than a tacit agreement.
2. **The golden system is the largest asset and also the most fragile single point.** Stage-by-stage golden data (.bin, f64 LE) + staged bisection is the core methodology of the project's 5 phases; but its regeneration depends entirely on the mosqito 1.2.1 + scipy version chain (Q5 X1). Asset and risk are two sides of the same thing.
3. **The dual-baseline strategy is a written decision** (`MOSQITO-VS-ISO-BASELINE-STRATEGY-2026-07-05.md`): mosqito golden data is the sole day-to-day baseline; the official ISO values govern compliance statements; the loyalty ceiling of parity is "compliant mosqito". New readers should read that document before the tests, otherwise they will mistake 1e-12 for a commitment to ISO (it is not; to ISO we commit only ±5%).
4. **Compatibility debt register**: pure implementation traces of mosqito (r8 rounding, nl wraparound, dead code such as the overwritten u2[0] initialisation) are "replicated but marked", not "believed correct". If upstream corrects them, we have a list to follow.
5. **The latency contract is the key number for real-time operation**: intrinsic algorithmic latency = 1 frame (0.5 ms) lookahead + <24 samples carry → `latency_samples() = 24` in R5. Everything downstream that claims "real time" (VST latency compensation, meter timestamps) builds on this constant; it deserves a dedicated test.
6. **The acceptance baseline lacks hardware counters** (Q3.1): record a perf/uProf baseline (cache hits, IPC, bandwidth) before R4 starts, otherwise the estimate "band-level parallelisation 19.6→4 ms" cannot be attributed and verified, and false sharing can only be guessed at.

---

## Conclusions at a glance

| Q | One-sentence answer |
|---|---|
| Q1 | Recursion cannot be parallelised along time → SIMD along the band axis (7×/5× f64x4) + branches turned into masks; multi-core only for frame-independent segments |
| Q2 | 1e-12 is a self-set engineering threshold (the standard requires only ±5%); precision equals Python's f64; the difference is verification 4–10 orders of magnitude stricter + 283× faster |
| Q3 | Cache hits not measured, cannot be called the limit (compute-bound by design); multi-core sacrifices zero precision (bit determinism); performance bounded by the Amdahl ceiling of 3.6× |
| Q4 | Scratch reuse, layout transposed to the access pattern, output de-materialisation, flat row-major; residual hot-path allocations registered, to be zeroed in R5 |
| Q5 | Most risks already explicitly registered (denormal, NaN, 48k, FFI panic, golden chain); the truly unregistered one is the pathological-input fuzz gap, added by this document |
| Q6 | Lock-free structure + fork-join tree waits + borrow checker make deadlock structurally impossible; wait semantics arrive with VST/FFI, countermeasures fixed (wait-free SPSC, one handle one thread) |
| Q7 | Determinism is a product feature, golden data is asset and single point, dual-baseline strategy is written down, latency contract 24 samples, hardware counter baseline before R4 |
