# Changelog

All notable changes to this project will be documented here. The project follows
[Semantic Versioning](https://semver.org/) for public API and ABI changes.

## Unreleased

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
