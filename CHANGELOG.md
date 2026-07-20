# Changelog

All notable changes to this project will be documented here. The project follows
[Semantic Versioning](https://semver.org/) for public API and ABI changes.

## Unreleased

### Added

- Bilingual public-review README files and a reproducible MoSQITo comparison script.
- Community, security, citation, contribution, and third-party notice files.

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

[Unreleased]: https://github.com/cclin99/iso532-1-rs/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/cclin99/iso532-1-rs/releases/tag/v0.1.0
