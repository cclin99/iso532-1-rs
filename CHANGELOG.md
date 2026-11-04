# Changelog

All notable changes to this project will be documented here. The project follows
[Semantic Versioning](https://semver.org/) for public API and ABI changes.

## 0.4.0 - Unreleased (pending independent verification)

Numeric release: the slope stage (`calc_slopes`) follows ISO 532-1:2017 Annex A,
and the correctness reference changes from MoSQITo 1.2.1 to the official Annex A
C program (decision `docs/C01-F03-SLOPE-ALIGNMENT-DECISION-2026-11-03.md`, plan
`docs/superpowers/plans/phases/phase-0.4.0-slope-annexa.md`). Every total
loudness value can change; no public API, output grid, stream contract, SIMD
dispatch, C ABI or Python shape changes.

### Changed

- F-04: the total loudness of each frame is no longer rounded to 0.001 sone
  (N <= 16) or 0.01 sone. The rounding came from MoSQITo `_calc_slopes`; Annex A
  does not round. The negative clamp is kept. Callers that want three decimals
  round themselves.
- F-05: when a band's slope segment starts in the band's last 0.1 Bark cell and
  meets the core loudness before `ZUP`, the band is now completed as in Annex A
  (flat remainder, or further slope segments clamped to `ZUP`) instead of being
  back-filled by the next band. This affected about 1% of time-varying frames
  by 1e-3 to 2.6e-2 sone each. Because the next band now starts from `ZUP`, the
  time-varying specific loudness of that next band changes too (towards Annex
  A); the specific value written in the completed cell is unchanged.
- F-07: specific loudness in the 0.1 Bark cell where a slope segment ends
  before the cell's sample. The rule kept from MoSQITo wrote the segment that
  started in that cell extrapolated past its end (below the core loudness);
  Annex A (`for (ZK = Z; ZK <= Z2; ...)`) writes each sample from the segment
  or flat part that contains it. Example: Annex B signal 18, frame 1564,
  Z = 3.7 Bark: 0.77011 -> 0.81388 sone/Bark (the band-4 core loudness, as the
  C program). Total loudness is bitwise unchanged (the `n` hashes did not
  move). Specific loudness against the Annex A C golden over whole series:
  4.4e-2 -> 2.1e-4 sone/Bark; against MoSQITo it now differs by design, up to
  3.1e-2 sone/Bark (time-varying, white_60 / annexb_sig5) and 8.0e-3
  (stationary, annexb_sig5).
- On 19,364 NL frames of Annex B signals 18/23/24/25 the slope stage equals the
  reference port `rust_slopes_fixed` (cross-analysis) bitwise and the Annex A
  algorithm with epsilon 0 and binary64 tables to <= 1.42e-14 sone.
- Correctness goldens: new `tools/gen_golden_c.py` builds the official
  `ISO_532-1.c` (SHA-256 `a74b45ed...834491`) with only `USL[12][4]` changed
  0.22f -> 0.24f (`tools/golden-c-usl12-4.diff`), MSVC x64 `/O2 /fp:precise`,
  and writes `data/golden-c/` (gitignored; manifest `tools/golden-c.sha256`).
  New `tests/golden_c.rs`, three tiers: the C-01 tail points (last output
  point of Annex B signals 18/23/24/25) at 1e-10 sone for total and specific
  loudness (measured <= 9.0e-11 and <= 3.3e-23); whole series, total, at 1e-4
  sone; whole series, specific, at 3e-4 sone/Bark. Whole-series agreement is
  limited by the C program itself (band-edge epsilon `_ZUP += .0001f` and
  float32 literals). Measured maxima over the nine golden signals and the four
  C-01 signals (Rust vs C with `USL[12][4]` = 0.24f, time-varying):

  | signal | total (sone) | specific (sone/Bark) |
  |---|---:|---:|
  | sine_1k_60 | 1.471e-7 | 6.184e-5 |
  | sine_250_80 | 2.022e-5 | 2.100e-4 |
  | sine_4k_60 | 4.987e-8 | 8.214e-5 |
  | white_60 | 1.915e-6 | 6.235e-5 |
  | pulse_1k_70 | 1.465e-7 | 1.097e-4 |
  | step_60_80 | 1.645e-6 | 1.297e-4 |
  | annexb_sig3 | 1.472e-7 | 6.184e-5 |
  | annexb_sig5 | 2.712e-5 | 6.235e-5 |
  | annexb_sig10 | 9.795e-8 | 1.097e-4 |
  | annexb_c01_sig18 | 6.614e-6 | 9.397e-5 |
  | annexb_c01_sig23 | 3.248e-7 | 8.249e-5 |
  | annexb_c01_sig24 | 1.753e-6 | 6.217e-5 |
  | annexb_c01_sig25 | 7.781e-7 | 8.249e-5 |

  Stationary (main loudness + slopes on the C golden's levels): total <=
  1.530e-5 sone, specific <= 1.500e-4 sone/Bark. The specific bound is the
  measured maximum rounded up to one significant digit.
- MoSQITo goldens are a compatibility check: `tests/golden_zwtv.rs`,
  `tests/golden_zwst.rs`, the slope total in `tests/golden_core.rs`, the sig10
  MoSQITo line in `tests/annexb.rs` and `iso532-py/tests/test_parity_mosqito.py`
  use a 5e-3 sone bound for the total loudness. Specific loudness against
  MoSQITo is recorded (maximum printed, finiteness asserted), not gated, since
  F-07 makes it differ by design; stage goldens keep their tolerances. Annex B
  verdicts are unchanged and pass.
- Frozen hashes: `N(t)` now carries the same libm/FMA ULP noise as
  `N_specific(t)` (the rounding used to hide it), so scalar and AVX2 differ by
  up to 2.6e-10 sone and the `n` hashes are per OS and backend.
  `tests/hash_gate.rs` and the `tests/golden_zwtv.rs` snapshots re-froze only
  `n` for F-04/F-05 and then only `n_specific` for F-07 (windows: local
  machine; linux: ubuntu:24.04, glibc 2.39); `time_axis` hashes are unchanged.
  The Python cross-language `N` hashes in `iso532-py/tests/test_smoke.py` are
  per platform now (`HASH_GATE_DUMP_ONLY=1` turns them into a dump; the CI py
  job sets it on windows like the Rust job), `TIME_HASH` is unchanged.
- `tests/nl_zero_init.rs` pins the 0.4.0 MoSQITo-tail reproduction numbers and
  keeps the audited pre-F-04 numbers within the rounding bound.
- F-03: `USL[12][4]` stays 0.24 provisionally (Table A.9 still PENDING). Against
  the unmodified C program (0.22) the C-01 tail points differ by up to 1.3e-7
  sone and whole series by up to 3.5e-3 sone (`docs/F03-USL12-4-STATUS-2026-10-31.md`).

### Fixed

- F-06: `core::calc_slopes*` no longer reads band 20 when starting band 0
  (`prev_grid_index(0) = 239` wrap-around). Direct calls with `nm[20] > nm[0]`
  returned a negative band-0 specific loudness and an inflated total (0.982
  instead of 0.4 sone for `nm[20] = 1` alone). Unreachable through the
  pipeline, whose main loudness keeps `nm[20] = 0`.

## 0.3.1 - 2026-11-01

Patch release: input contract and output-grid contract of the batch API, plus
test-only and documentation changes. No numeric output changes for finite input;
the C ABI gains one positive error code (additive, ABI v1 unchanged otherwise);
Python batch functions raise `ValueError` on NaN/Inf. Record:
`docs/RELEASE-0.3.1-2026-11-01.md`.

### Added

- `Iso532Error::NonFiniteInput { idx }` (stable code 4, C ABI
  `ISO532_ERR_NONFINITE_INPUT`): `loudness_zwst`, `loudness_zwtv` and
  `ZwtvProcessor::process*` now reject a NaN or infinite sample after the
  sample-rate and length checks and before any computation; `idx` is the first
  offending sample. Python raises `ValueError`. Previously the batch path
  returned `Ok` with zero loudness (audit finding C-02). The stream path is
  unchanged: it zeroes the sample and raises `FrameFlags::NONFINITE_INPUT`.
  Subnormal, zero and large finite samples remain valid input. The C ABI
  change is additive (new positive code); `iso532.h` regenerated with cbindgen.

### Changed

- Output-grid contract frozen (audit item C-01, decision 2026-11-01: keep ceil).
  `loudness_zwtv` and the stream return `ceil(ceil(L/24)/4)` points at exactly
  `96j/48000` s from 0; point `j` depends only on samples `<= 96j`. The official
  Annex A CLI grids (`floor(K/4)` total, `ceil(K/4)` specific, `K = floor(L/24)`)
  are documented as prefixes differing by at most one trailing point. New
  `tests/output_grid.rs` pins the count for 16 lengths (shortest legal, `24k±1`,
  `96k±1`, every `K mod 4` case), the exact time axis, stream count under any
  chunking, and prefix determinism bitwise under zero padding and under the real
  continuation of the signal. Documentation and tests only; no numeric or API
  change.
- Annex B tests (`tests/annexb.rs`) use the per-point tolerance of the official
  Annex B workbook, `max(0.1, 0.05 * |reference|)`, instead of the additive
  `0.1 + 0.05 * |reference|` (V-01). The verdict is fail-closed: empty curves,
  length mismatch, NaN/Inf on either side and negative reference values are
  `Invalid`, never a pass; the CSV reader no longer drops unparsable or blank
  rows silently. New `tests/annexb_validator.rs` pins the rule (including the
  10.55-vs-10.0 control that separates the two formulas), the invalid cases
  and the corrupted-file negatives on temp copies. Test-only change; no
  numeric or API effect. All existing Annex B tests pass under the max rule.

## 0.3.0 - 2026-10-31

Numeric behaviour change at the start of every time-varying result (finding
F-02, see Changed). Public Rust API gains `NlInit` and
`ZwtvProcessor::process_with`; the Python `loudness_zwtv` gains an `nl_init`
keyword; C ABI v1 is unchanged and follows the new default.

### Added

- `NlInit` (`Zero`, the default, and `MosqitoTail`) with
  `ZwtvProcessor::process_with`, `nl_loudness_with`, `nl_loudness_scalar_with`;
  `nl_loudness_avx2` now takes the initialisation explicitly.
- Python: `loudness_zwtv(signal, fs, field_type="free", nl_init="zero")`;
  `"mosqito_tail"` reproduces MoSQITo 1.2.1 for parity work.
- `tests/nl_zero_init.rs` (CI): batch prefix invariance against four future
  tails (bitwise on `N` and all 240 Bark rows), exactly zero loudness on a
  silent prefix, batch equal to the causal stream bitwise from frame 0,
  processor reuse, the audited pre-fix numbers pinned under `MosqitoTail`, and
  both initialisations identical when the signal ends in silence.
- Python parity: the zero-state default is cross-checked against MoSQITo run
  on the signal plus 0.5 s of silence, which makes MoSQITo's own seed exactly
  zero.
- `tests/golden_zwtv.rs`: zero-state convergence on the 10 s Annex B fixtures
  and a second frozen snapshot table for the default path.
- `tools/compare_mosqito.py --nl-init {zero,mosqito_tail}`; the README
  direct-comparison rows are re-measured for both initialisations (the
  default now differs from MoSQITo by 5.83e-3 sone at t = 2 ms on the 3 s
  contract signal; `mosqito_tail` reproduces the 2.66e-15 sone value).

### Changed

- F-02: the batch nonlinear temporal decay now starts from zero state
  (`UoLast = U2Last = 0` per band, ISO 532-1 Annex A C program) instead of the
  last-frame seed `core[-1] / 24` that MoSQITo 1.2.1 produces because its
  vectorised first column reads column `-1`. This is recorded as a finding and
  the project's current judgment (follow Annex A; the result for a signal
  prefix must not depend on later samples), not as a verdict on MoSQITo. The
  first 0.05-0.5 s of the result change by up to about 0.1-0.2 sone depending
  on the signal; signals ending in silence are bitwise unchanged; batch now
  equals the stream bitwise from frame 0. See
  `docs/F02-NL-ZERO-INIT-2026-10-31.md`.
- Frozen hashes re-recorded for the default path (`hash_gate` per OS, the
  `golden_zwtv` AVX2 snapshot, the Python contract `N` hash). Every previous
  value is retained and still asserted under `NlInit::MosqitoTail`, which
  attributes each change to the initialisation alone; `time_axis` hashes and
  the silent-tail fixtures (`pulse_1k_70`, `annexb_sig10`) are unchanged.
- `N_WARMUP_FRAMES` (580) and the `WARMUP` flag keep their value and semantics
  as a frozen v1 contract; they no longer mark a batch/stream difference.
- Stream and low-frequency gates compare batch against stream bitwise from
  frame 0 instead of within 1e-9 / 1e-6 after warm-up.

## 0.2.0 - 2026-10-31

Numeric behaviour change on a bounded input domain (see Fixed). Public Rust
API, C ABI v1, and Python interfaces are unchanged.

### Added

- Bilingual public-review README files and a reproducible MoSQITo comparison script.
- Community, security, citation, contribution, and third-party notice files.
- `tests/low_freq_correction.rs`: self-contained F-01 regression gate (28-band
  core, ZWST, ZWTV, and stream) pinned to ISO 532-1 Annex A C program values,
  plus per-threshold unit tests for the DLL row selection; wired into CI.
- CI now also runs the self-contained `stream_alloc`, `stream_no_rayon`, and
  `stream_scalar` integration tests on every push.
- Independent audit and verification reports under `docs/` (`修正報告.md`,
  `修正報告2.md`, `修正後獨立驗證報告.md`,
  `iso532-1-rs-code-review-remediation.md`). They were produced outside this
  repository; the evidence archives and the ISO Annex A C sources they cite
  are not redistributed here.

### Changed

- Test helper `read_bin` (and the SOS-row reader in `golden_dsp`) now rejects
  a golden file whose length is not a whole number of records instead of
  silently dropping the trailing bytes.

### Fixed

- **F-01, numeric behaviour change.** The low-frequency level correction
  (ISO 532-1 Annex A, RAP/DLL table) never selected the last DLL row. Levels in
  the 25-250 Hz bands above the seventh RAP threshold (for example > 118 dB on
  the 25 Hz band, > 112 dB on 31.5 Hz, > 100-109 dB on most other low bands)
  received a 0 dB correction instead of the table's last row. A 118.000001 dB
  25 Hz band produced 154.93 sone where the Annex A C program gives 52.51; a
  2 s 25 Hz / 119 dB SPL sine gave 165.19 sone (ZWST) and 172.13 sone (ZWTV
  max) against 56.70 / 56.88. Batch ZWST, batch ZWTV, and the stream path all
  shared the behaviour. Results for low-band levels at or below the seventh
  threshold are bitwise unchanged; the nine MoSQITo golden fixtures and the
  frozen hash gate are unaffected. The behaviour was inherited from MoSQITo
  1.2.1 (`_main_loudness.py`, `arange(1, 7)`); the same loop is present on
  upstream master as of 2026-10-31. This is recorded as a finding and the
  project's current judgment (follow Annex A), not as a verdict on MoSQITo;
  this crate now diverges from MoSQITo on that input domain. See
  `docs/F01-LOW-FREQ-DLL-ROW-FIX-2026-10-31.md`.

## 0.1.0 - 2026-07-19

### Added

- ISO 532-1 stationary and time-varying loudness in Rust.
- Scalar and AVX2+FMA execution with parity and determinism tests.
- Band-parallel batch processing with a sequential path.
- Stateful 48 kHz streaming output on a 2 ms grid, including sone, phon, frame
  flags, reset, and flush semantics.
- Frozen C ABI v1 and Python batch/stream bindings.
- MoSQITo 1.2.1 golden-generation, hash, Annex B, FFI, and Python verification
  workflows.

[Unreleased]: https://github.com/cclin99/iso532-1-rs/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/cclin99/iso532-1-rs/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/cclin99/iso532-1-rs/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/cclin99/iso532-1-rs/releases/tag/v0.1.0
