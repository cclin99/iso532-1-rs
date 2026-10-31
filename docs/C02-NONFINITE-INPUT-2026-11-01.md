# C-02 Non-finite batch input: contract and completion record

> 對照／Pair: [中文版](C02-NONFINITE-INPUT-2026-11-01.zh-TW.md) · source: zh · synced 2026-11-01

Date 2026-11-01 (Asia/Taipei). Base `28f6a49` (v0.3.0 + V-01). Implemented by Claude on the user's decision "C02 按照建議做" (do it as recommended). Audit origin: `docs/修正報告2.md` §12.2 row C-02.

## 1. Finding and contract

Before this change the batch functions accepted NaN and infinite samples and returned `Ok` with zero loudness, so a caller could not tell corrupt input from silence. The stream path already zeroed such samples and raised `FrameFlags::NONFINITE_INPUT`; that behaviour is correct for an audio thread, which must never fail.

Contract from this change on:

| path | behaviour on NaN / ±Inf | rationale |
|---|---|---|
| batch `loudness_zwst`, `loudness_zwtv`, `ZwtvProcessor::process*` | `Err(Iso532Error::NonFiniteInput { idx })`, stable code **4**, `idx` = first offending sample; nothing computed, nothing written | the batch has the whole signal; rejecting is the honest contract |
| C ABI `iso532_loudness_zwst` / `iso532_loudness_zwtv` | return `ISO532_ERR_NONFINITE_INPUT` (= 4); output buffers untouched | additive positive code, ABI v1 unchanged otherwise |
| Python `loudness_zwst` / `loudness_zwtv` | `ValueError` whose message contains `non-finite sample … index N` | existing error mapping |
| stream (`ZwtvStream`, C ABI stream functions, Python `ZwtvStream`) | unchanged: sample zeroed, `NONFINITE_INPUT` flag on the next output frame, residual flag after `flush` | real-time path never fails, never allocates |

Order of checks in the batch entry points: sample rate → length → finiteness → computation. Subnormal values, exact zeros (±0.0) and large finite values (for example 1e300) are finite input and are not rejected by this check; a huge value may still end in `LevelExceeds120dB`, which is the existing contract.

## 2. What changed

| file | change |
|---|---|
| `iso532/src/error.rs` | `Iso532Error::NonFiniteInput { idx }`, `code() = 4`, `check_finite(&[f64])` helper, unit tests |
| `iso532/src/zwst/mod.rs`, `iso532/src/zwtv/mod.rs` | `Iso532Error::check_finite(signal)?` after the length check |
| `iso532-ffi/src/lib.rs` | `ISO532_ERR_NONFINITE_INPUT = 4` with doc comment; batch wrappers propagate via the existing `e.code()` |
| `iso532-ffi/include/iso532.h` | regenerated with cbindgen 0.29.4; the only diff is the new define and its comment |
| `iso532/tests/api_errors.rs` | code 4 frozen; NaN/+Inf/−Inf at head, middle and tail for both batch functions; first offending index; precedence of sample-rate and length errors; subnormal / zero / 1e300 not rejected as non-finite; stream still flags |
| `iso532-ffi/tests/ffi.rs` | code 4 in the error-mapping table for zwtv and zwst with "nothing written" checks; constant frozen |
| `iso532-py/tests/test_smoke.py` | 9 parametrised cases (3 values × 3 positions) for both batch functions |
| `README.md`, `README.zh-TW.md`, `CHANGELOG.md` | input-contract sentence and Unreleased entry |

No change to any numeric path: for finite input every function computes exactly as before (all golden, hash, parity and SIMD tests unchanged and passing).

## 3. Gate results

| gate | result |
|---|---|
| `cargo fmt --all --check` | clean |
| `cargo clippy --all-targets -- -D warnings` (from `iso532/`) and `--workspace --all-features` | clean |
| `REQUIRE_AVX2=1 cargo test --workspace --all-features` | all passed, 0 failed, 3 ignored (pre-existing); `api_errors` 10, `ffi` 17, error unit tests 2 |
| `tools/golden_manifest.py --verify` | 175 files match |
| `maturin develop --release` + `ISO532_REQUIRE_PARITY=1 pytest iso532-py/tests` | 56 passed (47 before + 9 new) |

Local note: the machine's page file is almost fully committed, so cargo was run with `-j 2`; this is an environment limit, not a test result.

## 4. Audit acceptance mapping (§12.2 row C-02)

| acceptance item | status |
|---|---|
| NaN / ±Inf at head, middle, tail | tested in Rust (3 × 3 × 2 functions), FFI (2 cases), Python (9 cases) |
| subnormal, very large finite, zero | tested: accepted as finite input |
| FFI / Python / Rust consistent mapping | code 4 ↔ `ISO532_ERR_NONFINITE_INPUT` ↔ `ValueError`; FFI writes nothing on error |
| stream recovery and flag | unchanged behaviour, re-asserted in `api_errors.rs` and the existing stream tests |
| parameter / length errors | precedence test added |
| "do not silently present zero loudness" | batch now errors; stream flags (documented as a deliberate difference) |

## 5. Out of scope

C-01 output length, the stationary front end, F-03. No change to the stream path. Version number unchanged; this ships with the next release (0.3.1 or 0.4.0 at the user's choice; the C ABI change is additive).
