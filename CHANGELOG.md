# Changelog

All notable changes to this project will be documented here. The project follows
[Semantic Versioning](https://semver.org/) for public API and ABI changes.

## Unreleased

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

[Unreleased]: https://github.com/cclin99/iso532-1-rs/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/cclin99/iso532-1-rs/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/cclin99/iso532-1-rs/releases/tag/v0.1.0
