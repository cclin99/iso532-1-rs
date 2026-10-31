# Baseline selection strategy: mosqito golden data vs ISO 532-1 theoretical values
> 對照／Pair: [中文版](MOSQITO-VS-ISO-BASELINE-STRATEGY-2026-07-05.zh-TW.md) · source: zh · synced 2026-11-01

**Date:** 2026-07-05
**Nature:** reference document (basis for a strategy decision)
**Preceding documents:** `DESIGN-DEVELOPMENT-2026-07-04.md` §10 (measured deviation), `ROADMAP.md` §1 (candidate follow-on standards)
**Scope:** maintenance of the existing ISO 532-1 implementation, and the choice of verification baseline for follow-on standards such as sharpness (DIN 45692), ECMA-418-2, ISO 532-2 and roughness.

---

## 1. Problem statement

We have measured that the mosqito zwst stationary path deviates by ±0.8% from the official ISO 532-1 Annex B reference values (Signal 3 +0.82%, Signal 5 −0.76%), while the zwtv time-varying path is almost exact (0/500 points outside tolerance). Before implementing follow-on standards, three questions must be answered:

1. Is this deviation **deliberate design** on the mosqito side? Is the cause a limitation of the Python implementation?
2. Should the verification target for follow-on standards be the **ISO theoretical values** or the **mosqito golden data**?
3. What is the decision rule when the two conflict?

---

## 2. Anatomy of the implementation cause of the deviation (evidence from mosqito source)

### 2.1 What the mosqito zwst front end actually does

The spectral front end of `loudness_zwst.py` calls mosqito's **general-purpose sound level meter utility** `sound_level_meter/noct_spectrum`, not the ISO reference filter bank. Step by step (`_n_oct_time_filter.py`):

| Step | Implementation | Basis |
|---|---|---|
| Filter design | scipy `butter(3, (w1, w2), 'bandpass', output='sos')`: 3rd-order Butterworth band-pass (bilinear transform, 6th-order IIR) | The comment explicitly cites **ANSI S1.1-1986** (same family as IEC 61260), not ISO 532-1 Annex A |
| Pre-decimation of low bands | For `fc < fs/200` (at 48 kHz, fc < 240 Hz, i.e. the 10 bands from about 25 to 200 Hz) first `scipy.signal.decimate(sig, q)`: Chebyshev-I 8th order + **filtfilt zero phase** | Numerical necessity: at fc=25 Hz and 48 kHz the normalised bandwidth is ~1e-3 and a direct design is ill-conditioned (the source comment itself admits "filter design issue [ref needed]") |
| Filtering | `sosfilt` (causal, one direction) | — |
| Level computation | **Whole-signal RMS** (`sqrt(mean(sig_filt²))`, including the filter start-up transient, no discard window) | — |
| 44.1 kHz input | `scipy.signal.resample` (FFT method) to 48 kHz | — |

The stationary reference values of ISO 532-1 Annex B, on the other hand, were produced with **the filter chain of the standard's own reference program** (recursive filter bank, advanced sample by sample). The band edge shapes of the two paths differ by ~0.1 dB; amplified through the loudness transformation stage this becomes the ±0.8% deviation in N.

### 2.2 Contrast: why zwtv is almost exact

The mosqito zwtv front end (`_third_octave_levels`) **ports the 28-band filter bank of the ISO reference program (Annex A BASIC/C) coefficient by coefficient**, because the front end of the time-varying method is prescriptive in the standard and leaves no freedom to substitute. This is exactly why our measurements show zwtv at 0/500 points outside tolerance against the official curve while zwst shows ±0.8%: **the deviation is not in the loudness mathematics; it lies entirely in the freely selectable spectral front end of zwst** (in §10.1, Signal 1, which feeds band levels directly, deviates by only +0.005%, which is the output quantisation step, proving that the transformation stage is exact).

### 2.3 Scope of replication in this crate

On the Rust side, `zwst/mod.rs` + `dsp/filtfilt.rs` replicate the mosqito path **at bit level**, including the Chebyshev-I 8th-order coefficients of scipy `decimate` and the odd-padding semantics of `sosfiltfilt`. This is the precondition for golden parity reaching 8.2e-14. In other words: **we inherit mosqito's ±0.8% deviation, and we inherit it deliberately** (compatibility first).

---

## 3. Analysis: is this deliberate design? Is it because of Python?

Conclusion: **it is a deliberate engineering choice, but not "deliberately manufacturing a deviation". The deviation is a side effect permitted by the standard and accepted by the authors. Python's performance reality is one of the main motives, but not the only one.** Four layers of argument:

### 3.1 The standard itself grants this freedom (primary reason)

The reference program of the stationary method of ISO 532-1 (Method 1) **takes 28 third-octave band levels as input**, not a time-domain signal. For obtaining band levels from a signal, the standard only requires third-octave analysis compliant with IEC 61260-1 class 1; **it does not require the Annex A filter bank** (that is a prescribed element of the time-varying method). So mosqito's choice of a Butterworth front end for zwst:

- **does not violate the standard**: ±0.8% is far inside the ±5% compliance tolerance;
- the Annex B stationary reference values happen to be generated with the standard's own filter chain, so any "compliant but different" filter implementation shows an offset of this magnitude. This is "the compliance freedom becoming visible", not a defect in the implementation.

### 3.2 Python performance reality (the part the user guessed: correct, but needs to be made precise)

The ISO reference filter bank must **advance recursive state sample by sample**, and such a loop is catastrophically slow in pure Python/numpy. The evidence is in mosqito itself:

- zwtv was **forced** to port the ISO filter bank (prescriptive in the standard), and as a result mosqito zwtv takes 22.4 s for a 10 s signal on this machine (**0.45× real time**, not even half of real time);
- zwst **can avoid** this cost: scipy's `butter`/`sosfilt`/`decimate` are all vectorised C code that processes the whole signal in one pass.

So the precise statement is: **under Python, "use scipy vectorised primitives whenever possible instead of hand-written per-sample loops" is a survival rule; zwst happens to have the freedom granted by the standard to do so, and mosqito did.** If the standard were prescriptive for the stationary front end as well, mosqito would have had to pay the performance cost as it did for zwtv. So this is the intersection of "freedom + performance motive"; the Python factor alone is not sufficient (zwtv is the counter-example).

### 3.3 Architectural motive of tool reuse

`noct_spectrum` is a **shared component across metrics** in mosqito (the sound level meter module, also serving spectral analysis and other functions). Maintaining one general IEC 61260-style filter bank shared by all metrics fits library economics better than maintaining a separate ISO-specific filter bank for zwst alone. ANSI S1.1/Butterworth is also the customary industry formulation (MATLAB `poctave` belongs to the same family).

### 3.4 The deviation components are of different nature; record them separately

| Component | Nature | Magnitude contribution |
|---|---|---|
| Butterworth vs ISO reference filter shape | compliance freedom (deliberate choice) | major (~0.1 dB band level → ±0.8% N) |
| Whole-signal RMS including start-up transient, no discard window | simplification (small effect on stationary signals several seconds long) | minor |
| Pass-band ripple of the low-band decimate (Cheby-8 filtfilt) | numerical necessity (not a deliberate deviation) | minor |
| Ripple of the 44.1→48 kHz FFT resample | convenience choice | source of the residual +0.025% in Signal 3 |

---

## 4. Baseline recommendation for follow-on standards

### 4.1 Main axis: mosqito golden parity (keep the current strategy)

Four reasons, ordered by importance:

1. **Verification density**: golden data can be generated for **any signal** (9 datasets, and any edge case can be added), and parity can be tested down to 1e-12. The official reference values cover only a handful of signals with tolerance ±5% / 0.1 sone, which is 10 orders of magnitude coarser. Regression detection capability is not in the same class.
2. **Debuggability**: on divergence from mosqito, the stage can be **located by bisection stage by stage** (feeding intermediate values into Python for comparison). This is the core methodology of the 5 phases of this project. Debugging against ISO paper values can only guess.
3. **Transferable compliance**: mosqito is already inside the ISO tolerance (independently confirmed by this project's §10 measurements: all signals are inside the ±5% band), so bit-level parity inherits compliance automatically. **But the transfer premise must be re-confirmed before each new metric starts** (see 4.3).
4. **Consistency for migrating users**: users migrating from mosqito receive bit-identical numbers; the trust cost is lowest.

### 4.2 Secondary axis: build an IsoReference mode only when a meaningful gap is measured

The `ZwstMode::IsoReference` of zwst (§10.2, reusing the zwtv front end) is the template for this strategy: **the mosqito path is the default (the golden system must not be broken); the ISO reference path is optional.** For follow-on standards, run the gap report first and then decide:

- gap ≪ tolerance and ≪ perceptual significance (sone display resolution 1e-3) → **do not build a second mode**; document it and move on;
- gap is a noticeable fraction of the tolerance, or user scenarios require reporting against the official baseline (certification, regulation) → build the optional mode.

### 4.3 Fixed preparatory work before each new standard starts (write into the plan template)

1. **Gap report first**: replicate the `iso_gap_report` method of §10 and measure the deviation of the mosqito reference implementation against the official validation data of that standard **before work starts, so that the amount of inherited deviation and the stage it concentrates in are known in advance.**
2. **Parity debt register**: pure implementation traces of mosqito (such as the `r8()` 1e-8 rounding in zwst/zwtv and the nl wraparound initialisation) are registered item by item as "compatibility debt" when replicated: replicate but mark, so that there is a list to follow if mosqito corrects them or if we offer an ISO mode later.
3. **Freedom map**: mark which parts of the standard are prescriptive (must be copied bit-exact from the reference program) and which are freedoms (mosqito's choice is only one option). The zwst/zwtv lesson is that this line decides where deviation appears.

### 4.4 Decision rule quick reference

| Situation | Choice |
|---|---|
| Day-to-day development, regression tests, SIMD parity | mosqito golden data (sole baseline) |
| Standard compliance statement | official validation data + standard tolerance (golden transfer + independent confirmation) |
| Certification / regulatory scenario requiring the official baseline values | an optional mode of the IsoReference kind (built only when the gap is meaningful) |
| mosqito conflicts with the official values beyond tolerance | treat as a mosqito finding, report upstream, record in our documentation and follow the official values |

Row 4 has not occurred so far (all measured deviations are inside tolerance), but the rule must be set in advance: **the loyalty ceiling of parity is "compliant mosqito", not "any mosqito".**

---

## 5. Conclusions

1. The ±0.8% deviation of mosqito zwst is a **deliberate engineering choice**: the standard grants freedom in the stationary front end, and mosqito trades it, via scipy vectorised primitives (Butterworth + decimate + whole-signal RMS), for acceptable performance under Python and for tool reuse across metrics. The deviation is an accepted side effect, compliant within the ±5% tolerance. "Because of the Python implementation" is one of the main motives, but only because the standard permits it: zwtv does not have this freedom, and there mosqito honestly paid the 0.45× real-time cost and ported coefficient by coefficient.
2. Follow-on standards **keep mosqito golden data as the main axis** (verification density, debuggability, transferable compliance, migration consistency). Official reference values serve for the gap report before each standard starts and for the final compliance confirmation; an optional IsoReference mode is built only when the gap is meaningful.
3. The three preparatory items in §4.3 of this document (gap report / parity debt register / freedom map) should be included in the phase plan template of every follow-on standard.
