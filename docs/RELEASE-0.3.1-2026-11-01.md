# Release record: v0.3.1 (2026-11-01)

> 對照／Pair: [中文版](RELEASE-0.3.1-2026-11-01.zh-TW.md) · source: en · synced 2026-11-01

Scope of this release: the batch input contract (audit item C-02: NaN or infinite
samples are rejected with a new stable error code instead of returning zero loudness),
the frozen output-grid contract (C-01: keep `ceil`, documented and pinned by tests),
the fail-closed Annex B validator (V-01, test-only), and the bilingual documentation
set. No numeric output changes for finite input: every golden, frozen-hash, parity
and Annex B test passes unchanged. The C ABI gains one positive error code and
stays ABI v1; the Python batch functions raise `ValueError` on non-finite input.

Patch version per the project's rule (2026-11-01): documentation, tests, additive
API/ABI and small fixes bump the patch number; numeric or breaking changes bump the
minor number.

## Commits since v0.3.0

| commit | content |
|---|---|
| `d623d32` | V-01 phase plan (Annex B validator, fail-closed) |
| `4f03530` | V-01: `tests/common/annexb_check.rs` with the workbook rule `max(0.1, 0.05·|ref|)`, `tests/annexb_validator.rs` (24 tests), strict CSV/bin readers |
| `8920e25` | F-03 independent-verification deliveries (sensitivity, authority, SQAT) and status document |
| `28f6a49` | C-01 decision memo |
| `d7f438d` | C-02: `Iso532Error::NonFiniteInput { idx }` (code 4), `ISO532_ERR_NONFINITE_INPUT`, Python `ValueError`; tests in Rust, FFI and Python |
| `a2c0410` | Documentation language policy, 20 paired en/zh-TW documents, `tools/doc_pairs.py`, docs index, F-03 option B brief |
| `d0bd38b` | C-01: output-grid contract in README, doc comments, C header and CHANGELOG; `tests/output_grid.rs` (7 tests) and a Python shape test; C-01 verification brief |
| release commit | version 0.3.1, CHANGELOG, CITATION, README direct-comparison rows, auditor amendments to the C-01 brief, this record |

## What changes for users

| path | before | from 0.3.1 |
|---|---|---|
| batch `loudness_zwst`, `loudness_zwtv`, `ZwtvProcessor::process*` with a NaN or ±Inf sample | `Ok` with zero loudness | `Err(Iso532Error::NonFiniteInput { idx })`, code 4, first offending index, nothing computed |
| C ABI batch functions | return 0 and write zeros | return `ISO532_ERR_NONFINITE_INPUT` (4); output buffers untouched |
| Python `loudness_zwst` / `loudness_zwtv` | arrays of zeros | `ValueError` naming the index |
| stream (`ZwtvStream`, C ABI stream, Python `ZwtvStream`) | sample zeroed, `NONFINITE_INPUT` flag | unchanged |
| output grid of `loudness_zwtv` and the stream | `ceil(ceil(L/24)/4)` points (undocumented) | same count, now a frozen contract: point `j` at exactly `96j/48000` s, value depends only on samples `≤ 96j`; CLI grids are prefixes |
| Annex B tests | additive tolerance `0.1 + 0.05·|ref|` | workbook rule `max(0.1, 0.05·|ref|)`, fail-closed on invalid data |

Order of checks in the batch entry points: sample rate → length → finiteness →
computation. Subnormal, zero and large finite values remain valid input.

## Verification

### Local, release commit state

- Toolchain: rustc / cargo 1.99.1, Windows 10 x64, AVX2+FMA, 12 logical processors.
  Builds ran with `-j 2` because the machine's page file is almost fully committed;
  this is an environment limit, not a test result.
- `cargo fmt --all --check`: clean.
- `cargo clippy --all-targets -- -D warnings` (from `iso532/`, the CI command) and
  `cargo clippy --workspace --all-features --all-targets -- -D warnings`: clean.
- `REQUIRE_AVX2=1 cargo test --workspace --all-features`: 138 passed, 0 failed,
  3 ignored (hash dump, Python contract dump, silence throughput). New since 0.3.0:
  `annexb_validator` (24), `output_grid` (7), `api_errors` +6, `ffi` +2 cases,
  error unit tests +2.
- `tools/golden_manifest.py --verify`: 175 files match.
- Python: `maturin develop --release`, then `pytest iso532-py/tests` with
  `ISO532_REQUIRE_PARITY=1`: 69 passed (47 in 0.3.0, +9 non-finite cases, +13
  output-grid cases).
- `python tools/doc_pairs.py --check`: ok. `python tools/redact_paths.py --check docs`:
  clean.

### CI

- Run 41216048341 (`28f6a49`), 41219574093 (`a2c0410`), 41257789141 (`d0bd38b`): all
  six jobs green (test, ffi, py on ubuntu-latest and windows-latest), including the
  Linux frozen hash gate, which is unchanged by this release.
- The release commit's run result is recorded in the tag message.

### Independent verification

Pending before the tag (user decision 2026-11-01: independent verification first). The
acceptance round on release commit `30e4279` is briefed in
`docs/verification/briefs/2026-11-01-release-0.3.1-acceptance.md`: C-02 through an
independent harness in Rust, C and Python; the C-01 grid contract on real Annex B
signals; the V-01 validator's fail-closed controls; bitwise comparison with `v0.3.0` on
every Annex B signal for finite input; artifact hashes and exports; record consistency.
Its delivery goes to `docs/verification/2026-11-01-release-0.3.1-30e4279/` and this
section is updated from it before `v0.3.1` is created. Until then the C-02 change is
covered only by the acceptance items of `docs/修正報告2.md` §12.2 row C-02 (mapped in
`docs/C02-NONFINITE-INPUT-2026-11-01.md` §4). The C-01 numerical acceptance (official C
library value for the trailing point of Annex B signals 18/23/24/25) is a separate
brief, `docs/verification/briefs/2026-11-01-C01-zero-pad-reference.md`; it cannot change
the grid, only close or keep open the audit row, and does not gate the tag.

## Artifacts (built from the release commit state, Windows x64, rustc 1.99.1)

| file | SHA-256 |
|---|---|
| `iso532-0.3.1-cp39-abi3-win_amd64.whl` | `841584a2741029f23d8f66b5ff8ba72af0061a5d948248a61a7ef155c095f747` |
| `iso532_ffi.dll` | `c2d1b9d310733ebd49208050213b41a16a0bc8acbd3c7527485ee2f9e160102e` |
| `iso532_ffi.dll.lib` | `e5b7a8f812cd9e6d8be7a22f15dd0493ef3ebda7920757f3858d1e63026c05a9` |
| `iso532.h` | `0f548fd348cb0e3999ce8892bec05d4a5afd53740eb695428ad0eca9a45b709b` |

The import library is byte-identical to v0.2.0 and v0.3.0 (no exported symbol
changed). `iso532.h` differs from v0.3.0 only by the `ISO532_ERR_NONFINITE_INPUT`
define, its comment and the output-grid comment on `iso532_zwtv_out_frames`. PE
binaries embed build metadata, so a rebuild on another machine is not expected to
reproduce the DLL and wheel hashes byte for byte.

## API migration

- Rust callers that match on `Iso532Error` exhaustively gain the `NonFiniteInput { idx }`
  arm. Callers that previously relied on zero loudness for corrupt input must filter or
  repair the signal before the batch call, or use the stream path, which keeps the flag
  semantics.
- C callers: handle return value 4 (`ISO532_ERR_NONFINITE_INPUT`); output buffers are
  not written on error, as for the other codes.
- Python callers: catch `ValueError` from `loudness_zwst` / `loudness_zwtv`.
- No signature changes. `zwtv_out_frames` / `iso532_zwtv_out_frames` remain the only
  correct way to size buffers; the formula is now documented but should not be copied.

## Release checklist walkthrough (`docs/RELEASE-CHECKLIST.md`)

| item | status |
|---|---|
| Review-draft blockquote in README files | not present |
| Re-run `tools/compare_mosqito.py` | see "MoSQITo comparison" below; README direct-comparison rows updated |
| "Reproduce the evidence" commands from a regenerated golden environment | run on the existing local golden environment (manifest verified, 175 files); not regenerated from scratch |
| `docs/GOLDEN-REGEN-SOP.md` prerequisites | unchanged |
| Capability and boundary statements vs tagged source | README input-contract sentence (C-02), output-grid paragraph (C-01) and Annex B max-rule wording (V-01) added; no other claims changed |
| `THIRD_PARTY_NOTICES.md`, `CITATION.cff`, `SECURITY.md`, templates | `CITATION.cff` version 0.3.1, date 2026-11-01; others unchanged |
| Antivirus scan of release artifacts | **pending manual step**: Avira is the active product on the build machine; scan the artifact folder and record product, version, hashes and result here before publishing binaries |
| SHA-256 checksums | listed above |
| Local-only files, archives, `data/`, credentials, machine paths not staged | `data/`, `tmp/` and archives gitignored; `redact_paths.py --check docs` clean |
| Verification deliveries indexed with size, SHA-256 and link | unchanged since 0.3.0; download links for the archives still pending upload |

## MoSQITo comparison (release commit state, rustc 1.99.1)

Same script, signal and protocol as the README table (3 s contract signal, one
warm-up, 30 measured iterations), Python 3.11.9, NumPy 2.4.6, MoSQITo 1.2.1:

| implementation | mean | sample SD | min / max | relative speed |
|---|---:|---:|---:|---:|
| ISO532 Rust through Python binding, `nl_init="zero"` | 13.480 ms | 0.840 ms | 11.696 / 15.501 ms | 500.57x |
| MoSQITo 1.2.1 `loudness_zwtv` | 6.747 s | 0.333 s | 6.555 / 8.144 s | 1.00x |

Direct numerical comparison on the same run:

| initialisation | max abs dN(t) | max abs dN_specific(t) | note |
|---|---:|---:|---|
| `nl_init="zero"` (default) | 5.826515e-03 sone | 3.245252e-02 sone/Bark | identical to the 0.3.0 release values: the only difference to MoSQITo is the F-02 initialisation |
| `nl_init="mosqito_tail"` | 2.664535e-15 sone | 3.455569e-15 sone/Bark | identical to the 2026-07-20 and 0.3.0 values |

The README performance table is left at its quiet-machine 2026-07-20 measurement; the
timing above is a release-time snapshot.

## Known open items (not addressed in 0.3.1)

- C-01 numerical acceptance: official C library value for the trailing point of Annex B
  signals 18/23/24/25 (brief issued; the grid itself is frozen and will not change).
- F-03: `USL[12][4]` 0.24 (this project, MoSQITo, SQAT) vs 0.22 (Annex A C program,
  1991 paper); Table A.9 of ISO 532-1:2017 still needed; option B (lineage through
  AARAE 2015 / 2014 C) briefed. The table is not changed in this release.
- Stationary front end (ROADMAP R2): whole-signal RMS (MoSQITo-compatible) versus the
  reference filter bank with a settling window; decision pending.
- N5 column and window, exact 1 % boundary: pending an authoritative source.
- `N_WARMUP_FRAMES = 580` keeps its v1 meaning.

## Downstream

`iso532-rs-panel` pins the engine by git tag. To take this release, change the tag in
`plugin/Cargo.toml` to `v0.3.1`, run `cargo update -p iso532`, and re-run the panel's
acceptance gates (P-01 to P-03). The panel uses the stream path, whose numbers and
flags are unchanged by this release; only batch callers see the new error.
