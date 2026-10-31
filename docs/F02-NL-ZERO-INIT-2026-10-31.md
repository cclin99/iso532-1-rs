# F-02: batch nonlinear temporal decay starts from zero state

- Date: 2026-10-31
- Scope: `iso532::zwtv` batch path (`loudness_zwtv`, `ZwtvProcessor`), both
  backends (scalar, AVX2+FMA), both field types. The stream path already started
  from zero state and is unchanged.
- Status: fixed; numeric behaviour change at the start of every time-varying result
- Framing: the MoSQITo comparison below is a finding made during verification plus this
  project's current judgment; it is not a verdict on MoSQITo

## Finding

ISO 532-1 Annex A models the nonlinear temporal decay as a two-capacitor network per
critical band. The reference C program initialises both capacitor voltages (`UoLast`,
`U2Last`) to zero before the first frame.

MoSQITo 1.2.1 (`_nonlinear_decay.py`) vectorises the recursion over the whole signal
with `uo_mat[:, col-1]`; at `col = 0` NumPy reads the last column, which holds the
last frame's 24th interpolation step, `core[:, -1] + (0 - core[:, -1]) / 24 * 23 =
core[:, -1] / 24`. Every band is therefore seeded with one twenty-fourth of its final
core loudness. The Rust batch path reproduced that seed on purpose (`mosqito_seed`,
documented as a compatibility choice in the README) so that stage and end-to-end
golden comparisons stayed exact.

The independent audit (`docs/修正報告.md` §4, `docs/修正後獨立驗證報告.md` §2)
reproduced the consequence: for two 1 s signals whose first 0.5 s are identical
silence, adding a 1 kHz / 80 dB tone to the second half changes the first 0.25 s of
the batch result by 0.113550559256 sone and the very first frame from 0 to
0.001623810180 sone, while the C program and the Rust stream give 0 for both. Current
judgment: follow Annex A. The result for a signal prefix must not depend on samples
that come after it.

## Reproduction (before / after, AVX2 default dispatch, this machine)

| case | before (tail seed) | after (zero state) | C program / stream |
|---|---:|---:|---:|
| silence 0.5 s + 1 kHz 80 dB: N at frame 0 | 0.001623810180 sone | 0 | 0 |
| same, max |dN| over the first 0.25 s vs all-silent signal | 0.113550559256 sone | 0 | 0 |
| same, max |dN'| over 240 Bark, first 0.25 s | 0.1677 sone/Bark | 0 | 0 |
| synth gate signal x3: first frame at which batch == stream to 1e-9 | 544 (`N_WARMUP_FRAMES` = 580) | 0 (bitwise) | - |

Measured size of the seed effect on the golden fixtures (default dispatch, batch
before vs after; "last differing frame" is the last third-octave frame at which any
of the 21 nonlinear-decay outputs differs bitwise, at 2000 frames/s):

| fixture | seed max (sone) | nl stage: frames differing / last differing | end-to-end max |dN| (sone) |
|---|---:|---:|---:|
| sine_1k_60 | 0.0511 | 88 / 100 | 0.0118 |
| sine_250_80 | 0.1909 | 151 / 161 | 0.0650 |
| sine_4k_60 | 0.0722 | 42 / 45 | 0.0046 |
| white_60 | 0.0332 | 65 / 250 | 0.0352 |
| step_60_80 | 0.1685 | 1001 / 1000 | 0.0558 |
| annexb_sig3 (10 s) | 0.0512 | 88 / 100 | 0.0118 |
| annexb_sig5 (10 s) | 0.0269 | 102 / 239 | 0.0378 |
| pulse_1k_70, annexb_sig10 (silent tail) | 0 | 0 / - | 0 (bitwise identical) |

The end-to-end difference outlives the nonlinear stage because the seeded slow
capacitor (`U2`, time constant 75 ms) and the temporal weighting filter carry it;
on the 10 s fixtures the two paths are within the golden tolerance from output frame
482 (signal 3) / 532 (signal 5) and bitwise identical from frame 1002 / 980.

## Fix

`NlInit { Zero, MosqitoTail }` selects the initial state. `loudness_zwtv` and
`ZwtvProcessor::process` use `Zero`; `ZwtvProcessor::process_with` and the lower-level
`nl_loudness_with` / `nl_loudness_scalar_with` / `nl_loudness_avx2` accept the choice
explicitly. The Python binding exposes it as `loudness_zwtv(..., nl_init="zero" |
"mosqito_tail")`. The 24-step interpolation, the look-ahead to the next frame, the
recursion order, the output grid and the stream latency are untouched. C ABI v1 has
no knob and follows the default.

`MosqitoTail` is kept so that the nine MoSQITo golden fixtures and the direct MoSQITo
parity suite remain bitwise comparable; it is documented as a parity tool, not a
measurement mode.

## Verification added

- `tests/nl_zero_init.rs` (self-contained, in CI): prefix invariance against four
  tails of different content and length, bitwise on `N` and all 240 Bark rows for the
  250 output frames determined by a 0.5 s prefix; exactly zero loudness on a silent
  prefix; batch equals the causal stream bitwise from frame 0 (synthetic signal and the
  audit counterexample); processor reuse; the audited pre-fix numbers pinned under
  `MosqitoTail`; both initialisations identical when the signal ends in silence.
  Fail-first record: with the pre-fix code three of the four API-only tests failed
  (`N frame 0 = 0.0016238101803973733`, `batch=0.0029794411839959064 stream=0`).
- Unit tests in `nonlinear_decay.rs`: seed formula, 1- and 2-frame inputs, silent-tail
  equality, a quiet start exposes the seed while a loud start overwrites it, AVX2 vs
  scalar for both initialisations.
- `tests/golden_zwtv.rs`: stage and end-to-end MoSQITo comparisons run under
  `MosqitoTail` with unchanged tolerances; the zero-state default is checked against
  the golden data on the silent-tail fixtures (bitwise identical to the compat path)
  and from frame 600 on the 10 s fixtures, bitwise identical to the compat path from
  frame 1100.
- `tests/stream.rs`, `tests/low_freq_correction.rs`: batch vs stream is now asserted
  bitwise from frame 0 instead of <= 1e-9 / 1e-6 after warm-up.
- Python: `test_zwtv_parity` runs the binding with `nl_init="mosqito_tail"` (exact
  MoSQITo comparison, tolerances unchanged); the new
  `test_zwtv_default_matches_mosqito_given_a_silent_tail` compares the default against
  MoSQITo run on the signal plus 0.5 s of silence, which makes MoSQITo's own seed
  exactly zero (0.5 s is enough: at most 0.177 s of silence drives every band's core
  loudness to exactly 0 on these fixtures).

## Frozen hashes: attribution

Every re-recorded constant is paired with the previous value, which is still asserted
under `MosqitoTail`. The only difference between the two runs is the initial state, and
the silent-tail fixtures (`pulse_1k_70`, `annexb_sig10`) have identical hashes in both
tables.

| gate | path | before (now `MosqitoTail`) | after (default `Zero`) |
|---|---|---|---|
| `hash_gate` windows scalar | n / n_specific | `f3215787aaa48fbe` / `ff98c57f3018ef94` | `a7c2a418292a1a46` / `16937b45e6e4155d` |
| `hash_gate` windows AVX2 | n / n_specific | `f3215787aaa48fbe` / `3f241da3fe334097` | `a7c2a418292a1a46` / `3d4b4b2df9073e48` |
| `hash_gate` linux scalar | n / n_specific | `f3215787aaa48fbe` / `6e181dac593b5fef` | `a7c2a418292a1a46` / `05dc55b516e20132` |
| `hash_gate` linux AVX2 | n / n_specific | `f3215787aaa48fbe` / `8213780cd5384fb0` | `a7c2a418292a1a46` / `197c1084aab28c59` |
| `golden_zwtv` sine_1k_60 | n / n_specific | `0b10971021634b4e` / `62496b610f7c223d` | `89eacdd9fbaa911f` / `f41af57bbf84a2a1` |
| `golden_zwtv` step_60_80 | n / n_specific | `40ac75b0dcaed5a8` / `2fdc839b4f702621` | `d8da35c757b04b89` / `ad4d8b343c25af1f` |
| `golden_zwtv` pulse_1k_70, annexb_sig10 | n / n_specific | unchanged | unchanged |
| Python contract (`test_smoke.py`) | n | `44e6822074554786` | `9c0b638bfb7758d6` |
| all gates | time_axis | `f076bcb342595537` | unchanged |

`n` is bitwise identical on Windows and Linux (as before); only `n_specific` carries
libm ULP noise. Linux values were recorded in an `ubuntu:24.04` container (glibc 2.39,
rustc 1.99.1), the same image as the GitHub runner.

## Consequences

- MoSQITo 1.2.1 parity is scoped once more: the default output differs from MoSQITo at
  the start of every signal whose last frame is not silent (up to roughly 0.1-0.2 sone,
  for the first 0.05-0.5 s depending on the signal). `NlInit::MosqitoTail` restores
  the MoSQITo numbers.
- Batch and stream now agree bitwise from the first frame. `N_WARMUP_FRAMES = 580` and
  the `WARMUP` flag keep their value and semantics as a frozen v1 contract; the flag no
  longer marks a batch/stream difference (doc comment updated).
- The panel pins the engine by git tag and is unaffected until its dependency is
  bumped.
- Pre-fix golden/hash constants remain in the tree under the `MosqitoTail` label, so
  no comparison against the previously verified numbers was lost.
