# Release record: v0.3.0 (2026-10-31)

Scope of this release: finding F-02 (the batch nonlinear temporal decay starts from
zero state, as in the ISO 532-1 Annex A C program, instead of the MoSQITo 1.2.1
last-frame seed). Numeric output changes at the start of every time-varying batch
result whose signal does not end in silence; the stream path, the stationary path,
and signals ending in silence are bitwise unchanged. Public Rust API gains `NlInit`
and `ZwtvProcessor::process_with`; the low-level `nl_loudness_avx2` takes an explicit
`NlInit`; Python `loudness_zwtv` gains `nl_init`; C ABI v1 is unchanged and follows
the new default.

Known open items are listed at the end. This release does not claim overall
ISO 532-1 compliance.

## Commits since v0.2.0

| commit | content |
|---|---|
| `437f51c` | F-02 fix: `NlInit`, zero-state default for scalar and AVX2, `tests/nl_zero_init.rs`, frozen hashes re-recorded under the default and retained under `MosqitoTail` |
| `a0897f0` | Python `nl_init` keyword, padded-silence MoSQITo parity cross-check |
| `5450d39` | `docs/F02-NL-ZERO-INIT-2026-10-31.md`, README divergence row, CHANGELOG |
| `0207951` | F-02 independent-verification delivery under `docs/verification/`, evidence index, `tools/redact_paths.py` |
| release commit | version 0.3.0, CHANGELOG, README direct-comparison rows, `compare_mosqito.py --nl-init`, this record |

## Verification

### Local, release commit state

- Toolchain: rustc / cargo 1.99.1 (`rustup default stable`), Windows 10 x64, AVX2+FMA,
  12 logical processors.
- `cargo fmt --all --check`: clean.
- `cargo clippy --all-targets -- -D warnings` (from `iso532/`, the CI command) and
  `cargo clippy --workspace --all-targets --all-features -- -D warnings`: clean.
- `REQUIRE_AVX2=1 cargo test --workspace --all-features`: 100 passed, 0 failed,
  3 ignored (hash dump, Python contract dump, silence throughput), including
  `nl_zero_init` (6), `low_freq_correction` (6), `stream` (11), FFI (17) and
  2 doctests. The first attempt with default build parallelism failed to compile
  the test binaries (`found invalid metadata files`, `handle_alloc_error`) while the
  machine's page file was fully committed; the re-run with `-j 3` compiled and
  passed. No test failed in either attempt.
- `tools/golden_manifest.py --verify`: 175 files match.
- Python: `maturin develop --release` (installs 0.3.0, `iso532.__version__ == "0.3.0"`),
  then `pytest iso532-py/tests` with `ISO532_REQUIRE_PARITY=1`: 47 passed
  (smoke, stream, `nl_init`, and 27 direct MoSQITo comparison cases).

### CI

- Run 21 (`5450d39`) and run 22 (`0207951`): all six jobs green (test, ffi, py on
  ubuntu and windows), including the Linux frozen hash gate re-recorded for the
  zero-state default.
- The release commit's run result is recorded in the tag message.

### Independent verification

[`docs/verification/2026-10-31-F02-5450d39/F02獨立驗證報告.md`](verification/2026-10-31-F02-5450d39/F02獨立驗證報告.md)
(frozen snapshot `5450d39`, official Annex A C program rebuilt with MSVC): F-02 PASS
within its scope. Prefix causality 48/48 bitwise on `N` and all 240 Bark rows; batch
equal to the causal stream bitwise from frame 0, 36/36; official C `f_nl` stage on the
same 21-band core 28/28 with max |delta| 1.78e-14; FFI/Python defaults 8/8; the
`MosqitoTail` negative control still reproduces the pre-fix numbers 4/4. On the
2 s / 25 Hz / 119 dB SPL sine the time-varying envelope exceptions fell from 1/1000
(`N`) and 56/240000 (`N'`) to 0/0. Overall project status remains PARTIAL because of
the open items below; none is a regression from this release.

## Artifacts (built from the release commit, Windows x64, rustc 1.99.1)

| file | SHA-256 |
|---|---|
| `iso532-0.3.0-cp39-abi3-win_amd64.whl` | `cb4bc0864392cc66d50cf7268584e833d4a63d8cfeb01bce5c6d7b2e4d3967b4` |
| `iso532_ffi.dll` | `92c2c26803fdf32caf6c1a479c7579e8b92d47fd31ac8d50a438c4e047db9e66` |
| `iso532_ffi.dll.lib` | `e5b7a8f812cd9e6d8be7a22f15dd0493ef3ebda7920757f3858d1e63026c05a9` |
| `iso532.h` | `8f49fe105a6e287736f78b0eea21eb41b7bbeef02edffb89c7750b419e0a79bb` |

`iso532.h` and the import library are byte-identical to v0.2.0 (C ABI v1 unchanged).
PE binaries embed build metadata, so a rebuild on another machine is not expected to
reproduce the DLL and wheel hashes byte for byte; source and input hashes are the
reproducible part.

## API migration

- `iso532::zwtv::nonlinear_decay::nl_loudness_avx2(core, n_time, mode)` is now
  `nl_loudness_avx2(core, n_time, mode, init)`. Callers of this low-level function
  pass `NlInit::Zero` for the new default or `NlInit::MosqitoTail` for the previous
  behaviour. `loudness_zwtv`, `ZwtvProcessor::process`, `nl_loudness`,
  `nl_loudness_with_mode`, the C ABI and the Python batch function keep their
  signatures and switch to the zero-state default.
- Anyone comparing against MoSQITo 1.2.1 at the 1e-15 level must pass
  `NlInit::MosqitoTail` / `nl_init="mosqito_tail"`; see the comparison below.

## Release checklist walkthrough (`docs/RELEASE-CHECKLIST.md`)

| item | status |
|---|---|
| Review-draft blockquote in README files | not present; nothing to remove |
| Re-run `tools/compare_mosqito.py` | see "MoSQITo comparison" below; README direct-comparison rows updated for both initialisations |
| "Reproduce the evidence" commands from a regenerated golden environment | run on the existing local golden environment (manifest verified, 175 files); not regenerated from scratch for this release |
| `docs/GOLDEN-REGEN-SOP.md` prerequisites | unchanged since v0.1.0 |
| Capability and boundary statements vs tagged source | README F-02 divergence row present since `5450d39`; numerical-difference table re-measured for this release; no other capability claims changed |
| `THIRD_PARTY_NOTICES.md`, `CITATION.cff`, `SECURITY.md`, templates | `CITATION.cff` version updated (date unchanged, same day); others unchanged |
| Antivirus scan of release artifacts | **pending manual step**: Avira is the active product; Windows Defender is disabled on the build machine. Scan the artifact folder with Avira and record product, version, hashes, and result here before publishing binaries |
| SHA-256 checksums | listed above |
| Local-only files, archives, `data/`, credentials, machine paths not staged | `data/` and archives gitignored; `python tools/redact_paths.py --check docs` prints `clean` |
| Verification deliveries indexed with size, SHA-256 and link | sizes and SHA-256 recorded in `docs/verification/README.md`; **download links still "link pending"** until the archives are uploaded to the shared drive. Archives are not committed |

## MoSQITo comparison (release commit, rustc 1.99.1)

Same script, signal and protocol as the README table (3 s contract signal, one
warm-up, 30 measured iterations), Python 3.11.9, NumPy 2.4.6, MoSQITo 1.2.1:

| implementation | mean | sample SD | min / max | relative speed |
|---|---:|---:|---:|---:|
| ISO532 Rust through Python binding, `nl_init="zero"` | 12.210 ms | 0.771 ms | 10.894 / 13.683 ms | 563.36x |
| MoSQITo 1.2.1 `loudness_zwtv` | 6.879 s | 0.109 s | 6.752 / 7.109 s | 1.00x |

Direct numerical comparison on the same run:

| initialisation | max abs dN(t) | max abs dN_specific(t) | location |
|---|---:|---:|---|
| `nl_init="zero"` (default) | 5.826515e-03 sone | 3.245252e-02 sone/Bark | t = 2 ms; the contract signal has no leading silence, so MoSQITo's `core[-1] / 24` seed is non-zero |
| `nl_init="mosqito_tail"` | 2.664535e-15 sone | 3.455569e-15 sone/Bark | identical to the README's 2026-07-20 values |

The second row shows that the shared decay loop is unchanged; the whole difference in
the first row is the initialisation. The README performance table is left at its
quiet-machine 2026-07-20 measurement; the timing above is a release-time snapshot.

## Known open items (not addressed in 0.3.0)

- V-01: `tests/annexb.rs::isoclose` uses an additive tolerance; the Annex B workbook uses
  `max(0.1, 5 %)`. Empty vectors, infinite references, and unparsable CSV rows are not
  rejected. Specification: `docs/修正報告2.md` section 12.2 and 15.5. Test-only change,
  no numeric effect; planned next.
- C-01: for signals whose length is not a multiple of 96 samples the batch output has
  `ceil(ceil(L/24)/4)` points, one more than the official CLI's total-loudness writer
  (`floor`); the official specific-loudness writer itself uses `ceil`. The extra point
  has no official reference value. Decision on the output-length contract pending.
- C-02: batch ZWST/ZWTV accept NaN and infinite samples and return `Ok` with zero
  loudness; the stream path zeroes the sample and raises `NONFINITE_INPUT`. Decision
  on reject / flag / substitute pending.
- Stationary front end: whole-signal RMS including filter start-up (MoSQITo-compatible)
  versus the reference filter bank with a settling window (`TimeSkip`); specific
  loudness at high low-frequency levels differs from the C program (66 of 240 Bark
  values at TimeSkip = 0.2 s) while total loudness stays in tolerance. Decision on the
  front-end contract pending.
- Official reference material questions (N5 column and window, exact 1 % boundary,
  `USL[12][4]` 0.24 in Rust and MoSQITo versus 0.22 in the Annex A C program, F-03)
  remain pending an authoritative source (ISO 532-1:2017 Table A.9 and clause text).
  The table is not changed in this release.
- `N_WARMUP_FRAMES = 580` and the `WARMUP` flag keep their v1 meaning; since F-02
  they no longer mark a batch/stream difference.

## Downstream

`iso532-rs-panel` pins the engine by git tag `v0.1.0`. To take this release, change the
tag in `plugin/Cargo.toml` to `v0.3.0`, run `cargo update -p iso532`, and re-run the
panel's own acceptance gates (P-01 to P-03); the panel's product version is independent
of the engine version. The panel uses the stream path, whose numbers are unchanged by
F-02; F-01 (v0.2.0) does affect it.
