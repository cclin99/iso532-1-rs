# Release record draft: v0.4.0 (2026-11-04, pending independent verification)

> 對照／Pair: [中文版](RELEASE-0.4.0-2026-11-04.zh-TW.md) · source: zh · synced 2026-11-04

**Status: draft.** No tag, no push, no CI run and no release artifacts yet; the tag follows Astra's independent verification. Implementer: Claude Opus 5.5, following [`superpowers/plans/phases/phase-0.4.0-slope-annexa.md`](superpowers/plans/phases/phase-0.4.0-slope-annexa.md) and the decision memo [`C01-F03-SLOPE-ALIGNMENT-DECISION-2026-11-03.md`](C01-F03-SLOPE-ALIGNMENT-DECISION-2026-11-03.md) (D1–D5). Starting point `5cb036a` (documentation commit after v0.3.1).

Scope: the slope stage (`calc_slopes_impl`) follows ISO 532-1:2017 Annex A, and the correctness reference changes from MoSQITo 1.2.1 to the official Annex A C program. This is a numeric change, so the minor version is raised under the versioning rule. API, output grid, stream contract, SIMD dispatch, C ABI and Python shapes are unchanged; `USL[12][4]` stays 0.24 (F-03, provisional).

## Commits since v0.3.1 (this phase)

| commit | content |
|---|---|
| `93ba5e4` | Task 1: three RED unit tests for F-04 / F-05 / F-06 |
| `d011921` | Task 2: `calc_slopes_impl` fix (no per-frame rounding, Annex A band completion, band 0 does not read band 20) |
| `9d8ae5a` | Task 3: contract and stream tests unchanged; the sig10 MoSQITo line in `annexb.rs` becomes a compatibility bound |
| `777d8e8` | Task 4: `tools/gen_golden_c.py`, `tools/golden-c-usl12-4.diff`, `tools/golden-c.sha256`, `tests/golden_c.rs` |
| `8beeb90` | Task 5: MoSQITo goldens as compatibility checks, `n` hashes re-frozen, version 0.4.0, CHANGELOG, README, F-03 status |
| commit holding this draft | Task 6: this record (both languages) |

## What users see

- Every total loudness value can change: no per-frame rounding to 0.001 / 0.01 sone (F-04); about 1% of time-varying frames change by 1e-3 to 2.6e-2 sone through the band completion (F-05) (≤ 3.9e-3 sone against the MoSQITo goldens after temporal weighting).
- On broadband input the time-varying specific loudness of the band after a completed band changes as well (it now starts from `ZUP`): up to 1.13e-2 sone/Bark against MoSQITo (white_60) and 9.0e-3 (annexb_sig5), closer to the Annex A C golden.
- Direct calls of `core::calc_slopes*` with `nm[20] > nm[0]` no longer produce a negative band-0 specific loudness (F-06); pipeline input is unaffected.
- `N(t)` is no longer bitwise identical across OSes and backends: scalar and AVX2 differ by up to 2.6e-10 sone. Downstream users of `n` hashes must re-freeze per platform.

## Verification (local, state `8beeb90`, Windows x64, rustc 1.99.1)

- `cargo fmt --all -- --check`, `cargo clippy --workspace --all-targets -- -D warnings`: clean.
- `cargo test --workspace`: 140 passed, 0 failed, 5 ignored (two of them are the whole-series 1e-10 `golden_c` comparisons, a known finding below). `cargo bench --workspace --no-run`: builds.
- Contract and stream: `output_grid` 7, `stream` 11 (1 pre-existing ignored), `stream_scalar` 1, `stream_no_rayon` 1, `simd_parity` 2, `determinism` 1, all passing with unchanged tests.
- Annex B: `annexb` 3 and `annexb_validator` 24 pass; the 500 ISO reference points of signal 10 have 0 exceptions (max |N − ref| 1.25e-4). The rule `max(0.1, 0.05·|ref|)` is unchanged.
- Linux (`ubuntu:24.04` container, glibc 2.39, rustc 1.99.1, Task 5 working tree with the same Rust code and tests as `8beeb90`): the CI test subset plus `nl_zero_init` passes, and `hash_gate` asserts the new Linux constants; the container's `n_specific` hashes equal the previously frozen ones.
- Python (0.4.0 wheel, `ISO532_REQUIRE_PARITY=1`): 83 passed, 4 xfailed (strict); see the known findings.

## Annex A C golden (D4 / D-D)

- Reference program: the official `ISO_532-1.c` (SHA-256 `a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491`) with only `USL[12][4]` changed from `0.22f` to `0.24f` (substituted source SHA-256 `739af24dee118027cb419fcdb051d8b56b274211d986140d66d7ff4b9d52a7e9`); MSVC 19.44.35228 x64, `/O2 /fp:precise`; the wrapper only calls `f_loudness_from_signal` and `f_loudness_from_levels`. Data files reproduce bitwise on a rerun (only the date in `meta.json` differs).
- C-01 tail points (last output point of Annex B signals 18/23/24/25):

| signal | Rust 0.4.0 − C golden (0.24f) | max specific diff | Rust 0.4.0 − unmodified C (0.22f) |
|---|---|---|---|
| 18 | −6.61e-11 | 9.1e-24 | −1.43e-8 |
| 23 | −5.16e-11 | 3.3e-23 | −1.28e-7 |
| 24 | −8.99e-11 | 2.2e-23 | −9.33e-9 |
| 25 | −7.41e-11 | 4.7e-24 | −7.41e-11 |

`unmodified_c_delta` in `meta.json` (C golden − unmodified C) is −1.42e-8 / −1.28e-7 / −9.24e-9 / 0, the magnitude stated in §2 of the decision memo (≤ 1.3e-7).

## Known findings (for the decision owner)

1. **Whole-series 1e-10 is not achievable.** Over whole series of the nine signals and the four C-01 signals, Rust 0.4.0 against the C golden differs by up to 2.7e-5 sone in total loudness (annexb_sig5) and up to 4.4e-2 sone/Bark in specific loudness (signal 18). The total difference comes from the official C program itself (`_ZUP += .0001f` and float32 literals; on identical NL input its slope stage already differs from Rust by up to 9.7e-6 per frame). The specific difference comes from the cell where a slope meets the core loudness: the MoSQITo rule extrapolates the slope below the core value, the C program writes the core value (e.g. signal 18 point 391 bark 36: Rust 0.7701, C 0.8139). That is another specific-pattern difference inherited from MoSQITo, left unchanged in this phase as planned. The 1e-10 gate is therefore enforced on the C-01 tail points only; the whole-series comparisons are kept as `#[ignore]`d strict tests.
2. **MoSQITo specific compatibility exceeds D-E.** F-05 changes the time-varying specific loudness of the next band; against MoSQITo white_60 / annexb_sig5 reach 1.13e-2 / 9.0e-3 sone/Bark, above 5e-3. The two Python parity cases are strict `xfail`; the Rust `golden_zwtv` end-to-end comparison never included these two signals. Whether to widen the compatibility bound is the decision owner's call.
3. **The Python `n` hash holds only on this Windows machine.** `test_smoke.py` now keeps per-platform `n` hashes; the Linux value uses the same glibc as GitHub runners, the Windows value only holds on the freezing machine. The CI py job does not set `HASH_GATE_DUMP_ONLY`, so windows-latest will probably fail; CI needs that variable (as in the Rust job) or a value measured on CI. CI was not changed in this phase.

## Not done / open

- No tag, no push, no GitHub CI run, no release artifacts.
- `CITATION.cff` still says 0.3.1: version and `date-released` were updated in the release commit in the past, and the release date is not known yet.
- `tools/doc_pairs.py --check` reports one pre-existing error: the pair line of `C01-F03-SLOPE-ALIGNMENT-DECISION-2026-11-03.md` reads "Pair／對照"; it already exists at `5cb036a` and the decision memo was not edited in this phase.
- F-03 (Table A.9) remains PENDING; the stationary front end is still undecided.
