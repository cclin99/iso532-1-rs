# Release record: v0.2.0 (2026-10-31)

> 對照／Pair: [中文版](RELEASE-0.2.0-2026-10-31.zh-TW.md) · source: en · synced 2026-11-01

Scope of this release: finding F-01 (ISO 532-1 Annex A low-frequency RAP/DLL
correction now selects the last table row). Public Rust API, C ABI v1, and the
Python interface are unchanged. Numeric output changes only for low-band levels
above the seventh RAP threshold; everything else is bitwise identical to v0.1.0.

Known open items are listed at the end. This release does not claim overall
ISO 532-1 compliance.

## Commits since v0.1.0

| commit | content |
|---|---|
| `ae55ca1`, `73d110e`, `8fde6b6`, `603726b` | README, governance files, performance measurements (docs only) |
| `3dc420c` | F-01 fix, `low_freq_dll_row`, per-threshold unit tests, `tests/low_freq_correction.rs`, docs |
| `6aea8b3` | test readers use `as_chunks` and reject trailing partial records (clippy 1.99) |
| release commit | version 0.2.0, CHANGELOG, CI stream tests, neutral wording, audit reports under `docs/` |

## Verification

### Local, release commit state

- Toolchain: rustc / cargo 1.99.1 (`rustup default stable`), Windows 10 x64, AVX2+FMA.
- `cargo fmt --all --check`: clean.
- `cargo clippy --all-targets -- -D warnings` (from `iso532/`, the CI command) and
  `cargo clippy --workspace --all-targets --all-features -- -D warnings`: clean.
- `REQUIRE_AVX2=1 cargo test --workspace --all-features`: every suite green, including
  the nine MoSQITo golden fixtures, Annex B signals 3/5/10, SIMD parity, determinism,
  the frozen Windows hash gate, all stream suites, and FFI (17).
- `tools/golden_manifest.py --verify`: 175 files match.
- Python: `maturin develop --release`, then `pytest iso532-py/tests` with
  `ISO532_REQUIRE_PARITY=1`: 36 passed (smoke, stream, and direct MoSQITo parity).

### CI

- Run 18 (`3dc420c`): clippy failed on both runners because the hosted stable toolchain
  had moved to 1.99.1 (`chunks_exact_to_as_chunks` on pre-existing test code); tests did
  not run.
- Run 19 (`6aea8b3`): all six jobs green (test, ffi, py on ubuntu and windows), including
  the Linux frozen hash gate and `low_freq_correction`.
- The release commit adds `stream_alloc`, `stream_no_rayon`, `stream_scalar` to the CI
  test list; its run result is recorded in the tag message.

### Independent verification

`docs/修正後獨立驗證報告.md` (frozen snapshots `3dc420c` and `6aea8b3`, official Annex A
C program rebuilt with MSVC): F-01 PASS within its scope (337 original boundary cases
and 1,210 new free/diffuse cases, 0 tolerance failures; 25 Annex B cases unchanged,
188 stored outputs bitwise identical to v0.1.0). Overall project status remains PARTIAL
because of the open items below, none of which is a regression from this release.

## Artifacts (built from the release commit, Windows x64, rustc 1.99.1)

| file | SHA-256 |
|---|---|
| `iso532-0.2.0-cp39-abi3-win_amd64.whl` | `091b605abaab393f2aa73b6257bd0b9090bd7b6a594a2962800f8ba13a244b74` |
| `iso532_ffi.dll` | `f59ab3d4eea6eb8999ada992795cb253420652bdc7d374d2e8d6e79e466fb15d` |
| `iso532_ffi.dll.lib` | `e5b7a8f812cd9e6d8be7a22f15dd0493ef3ebda7920757f3858d1e63026c05a9` |
| `iso532.h` | `8f49fe105a6e287736f78b0eea21eb41b7bbeef02edffb89c7750b419e0a79bb` |

PE binaries embed build metadata, so a rebuild on another machine is not expected to
reproduce these hashes byte for byte; source and input hashes are the reproducible part.

## Release checklist walkthrough (`docs/RELEASE-CHECKLIST.md`)

| item | status |
|---|---|
| Review-draft blockquote in README files | not present; nothing to remove |
| Re-run `tools/compare_mosqito.py` | see "MoSQITo comparison" below |
| "Reproduce the evidence" commands from a regenerated golden environment | run on the existing local golden environment (manifest verified); not regenerated from scratch for this release |
| `docs/GOLDEN-REGEN-SOP.md` prerequisites | unchanged since v0.1.0; tools referenced (`setup_env.sh`, `gen_golden.py`, `golden_manifest.py`, `requirements.lock`) all present |
| Capability and boundary statements vs tagged source | README inherited-choices table updated for F-01; no other capability claims changed |
| `THIRD_PARTY_NOTICES.md`, `CITATION.cff`, `SECURITY.md`, templates | `CITATION.cff` version and date updated; others unchanged |
| Antivirus scan of release artifacts | **pending manual step**: the active product on the build machine is Avira Security; Windows Defender is disabled (`MpCmdRun` returns 0x80004005). Scan the artifact folder with Avira and record product, version, hashes, and result here before publishing binaries |
| SHA-256 checksums | listed above |
| Local-only files, archives, `data/`, credentials, machine paths not staged | `data/` and archives are gitignored. The audit reports under `docs/` were written outside this repository and contain reproduction command lines with absolute paths from the auditor's workstation; they are included unmodified as audit evidence |

## MoSQITo comparison (release commit, rustc 1.99.1)

Same script, signal, and protocol as the README table (3 s contract signal, one
warm-up, 30 measured iterations), Python 3.11.9, NumPy 2.4.6:

| implementation | mean | sample SD | min / max | relative speed |
|---|---:|---:|---:|---:|
| ISO532 Rust through Python binding | 16.889 ms | 3.594 ms | 13.345 / 30.285 ms | 452.22x |
| MoSQITo 1.2.1 `loudness_zwtv` | 7.637 s | 0.688 s | 7.129 / 9.922 s | 1.00x |

Direct numerical comparison on the same run: max |dN(t)| = 2.664535e-15 sone and
max |dN_specific(t)| = 3.455569e-15 sone/Bark, identical to the values recorded in the
README for v0.1.0, which is the expected outcome because the comparison signal does not
enter the F-01 domain.

The timing columns were measured while the machine was also running the independent
verification and release builds (sample SD 3.6 ms against 0.45 ms in the README
measurement), so they are recorded here as a release-time snapshot and the README
performance table is left at its quiet-machine 2026-07-20/21 measurements. Re-measure
on an idle machine before quoting new timing figures.

## Known open items (not addressed in 0.2.0)

- F-02: batch nonlinear-decay state is seeded from the final frame (MoSQITo-compatible);
  the official C program starts from zero. The stream path already starts from zero.
  Planned as a separate numeric change (0.3.0) with a from-0 ms, all-Bark regression
  test; the 25 Hz / 119 dB time-varying onset shows the effect.
- V-01: `tests/annexb.rs::isoclose` uses an additive tolerance; the Annex B workbook uses
  `max(0.1, 5 %)`. Empty vectors, infinite references, and unparsable CSV rows are not
  rejected.
- C-02: batch ZWST/ZWTV accept NaN and infinite samples and return `Ok` with zero
  loudness; the stream path zeroes the sample and raises `NONFINITE_INPUT`.
- Stationary front end: whole-signal RMS including filter start-up (MoSQITo-compatible)
  versus the reference filter bank with a settling window; specific loudness at high
  low-frequency levels differs from the C program while total loudness stays in
  tolerance.
- Official reference material questions (N5 column and window, exact 1 % boundary,
  USL[12][4] 0.24 vs 0.22) remain pending an authoritative source.
- `N_WARMUP_FRAMES = 580` was frozen on the synthetic test signal; on the 25 Hz / 119 dB
  sine the stream matches batch to 1e-9 only from frame 597.

## Downstream

`iso532-rs-panel` pins the engine by git tag `v0.1.0`. To take this release, change the
tag in `plugin/Cargo.toml` to `v0.2.0`, run `cargo update -p iso532`, and re-run the
panel's own acceptance gates; the panel's product version is independent of the engine
version.
