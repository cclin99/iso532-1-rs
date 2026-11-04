# Release record: v0.4.0 (2026-11-04)

> 對照／Pair: [中文版](RELEASE-0.4.0-2026-11-04.zh-TW.md) · source: zh · synced 2026-11-05

**Status:** Astra's independent acceptance of the candidate `fca4ccd` is delivered with verdict PARTIAL and no numeric or API release blocker (see "Independent verification"). The tag `v0.4.0` goes on the commit that records that section, and the CI result after the push is recorded in the tag message; no release artifacts are built. Implementer: Claude Opus 5.5, following [`superpowers/plans/phases/phase-0.4.0-slope-annexa.md`](superpowers/plans/phases/phase-0.4.0-slope-annexa.md) and the decision memo [`C01-F03-SLOPE-ALIGNMENT-DECISION-2026-11-03.md`](C01-F03-SLOPE-ALIGNMENT-DECISION-2026-11-03.md) (D1–D5, revised in §7). Round 1 started at `5cb036a` (documentation commit after v0.3.1); Round 2 started at `9301c0d` (decision revision after the first verification).

Scope: the slope stage (`calc_slopes_impl`) follows ISO 532-1:2017 Annex A, and the correctness reference changes from MoSQITo 1.2.1 to the official Annex A C program. This is a numeric change, so the minor version is raised under the versioning rule. API, output grid, stream contract, SIMD dispatch, C ABI and Python shapes are unchanged; `USL[12][4]` stays 0.24 (F-03, provisional).

## Commits since v0.3.1 (this phase)

| commit | content |
|---|---|
| `93ba5e4` | Round 1 Task 1: three RED unit tests for F-04 / F-05 / F-06 |
| `d011921` | Round 1 Task 2: `calc_slopes_impl` fix (no per-frame rounding, Annex A band completion, band 0 does not read band 20) |
| `9d8ae5a` | Round 1 Task 3: contract and stream tests unchanged; the sig10 MoSQITo line in `annexb.rs` becomes a compatibility bound |
| `777d8e8` | Round 1 Task 4: `tools/gen_golden_c.py`, `tools/golden-c-usl12-4.diff`, `tools/golden-c.sha256`, `tests/golden_c.rs` |
| `8beeb90` | Round 1 Task 5: MoSQITo goldens as compatibility checks, `n` hashes re-frozen, version 0.4.0, CHANGELOG, README, F-03 status |
| `2fc1708` | Round 1 Task 6: first draft of this record (both languages) |
| `5bbbb93` | Fix of the pair line of the English decision memo (documentation only) |
| `fe3d0b2`, `9301c0d` | Decision revision after the first verification (F-07, tiered C-golden gates) and the Round 2 plan |
| `a1a261d` | Round 2 Task 7: RED unit tests for F-07 |
| `0bb2272` | Round 2 Task 8: F-07 fix, `n_specific` hashes re-frozen, whole-series C-golden gates, MoSQITo specific loudness recorded, `HASH_GATE_DUMP_ONLY` in the CI py job |
| `fca4ccd` | Round 2 Task 9: CHANGELOG, README, this record (both languages); the verified candidate snapshot |
| `7900035`, `b119d20`, later | Acceptance brief, delivery of the independent round (with a `.gitattributes` that applies only to that delivery folder), this section; documentation and verification evidence only. The crate sources at the tag are identical to the verified `fca4ccd`. |

## What users see

- Every total loudness value can change: no per-frame rounding to 0.001 / 0.01 sone (F-04); about 1% of time-varying frames change by 1e-3 to 2.6e-2 sone through the band completion (F-05) (≤ 3.9e-3 sone against the MoSQITo goldens after temporal weighting).
- In the cell where a slope segment ends before the cell's sample, the specific loudness is now the value of the segment that contains the sample (F-07); e.g. signal 18 frame 1564 at 3.7 Bark goes from 0.77011 to the core loudness 0.81388. Total loudness is not affected (bitwise identical). The band after a completed band starts at `ZUP` (F-05), which also changes its time-varying specific loudness. Together, the whole-series specific difference against the Annex A C golden drops from 4.4e-2 to 2.1e-4 sone/Bark; against MoSQITo it now differs by design, up to 3.15e-2 sone/Bark time-varying (annexb_sig5) and 7.96e-3 stationary (annexb_sig5).
- Direct calls of `core::calc_slopes*` with `nm[20] > nm[0]` no longer produce a negative band-0 specific loudness (F-06); pipeline input is unaffected.
- `N(t)` is no longer bitwise identical across OSes and backends: scalar and AVX2 differ by up to 2.6e-10 sone. Downstream users of `n` or `n_specific` hashes must re-freeze per platform.

## Verification (local, state `0bb2272`, Windows x64, rustc 1.99.1)

- `cargo fmt --all -- --check`, `cargo clippy --workspace --all-targets -- -D warnings`, and `cargo clippy --all-targets --all-features -- -D warnings` in `iso532-ffi`: clean.
- `cargo test --workspace`: 146 passed, 0 failed, 3 ignored (all three are pre-existing manual helpers or performance tests: `dump_zwtv_output_hashes`, `dump_py_bitwise_contract_hashes`, `silence_throughput_within_20pct_of_sine`). `cargo bench --workspace --no-run`: builds.
- F-07: `f07_sample_after_segment_end_is_core_or_next_segment` FAILED before the fix (`spec[36]` 0.770106544821296590 vs `nm[4]` 0.813879371664140705) and passes after it; the frame total is bitwise identical before and after (`0x401fc356fc47a15a`). `f07_specific_matches_the_annex_a_reference_port`: a binary64 port of the official `f_calc_slopes` (without the band-edge epsilon) matches total and all 240 cells to 1e-9 on 507 frames.
- `hash_gate.rs`: `n` and `time_axis` are unchanged on every platform; only `n_specific` was re-frozen (old and new values below). The `golden_zwtv.rs` AVX2 snapshots likewise changed only in the `n_specific` column.
- Annex B: `annexb` 3 and `annexb_validator` 24 pass; the rule `max(0.1, 0.05·|ref|)` is unchanged.
- Linux (`ubuntu:24.04` container, glibc 2.39, rustc 1.99.1, `git archive` of `0bb2272`): `cargo test --lib` 30 passed; `hash_gate` asserts the new constants; the CI test subset plus `nl_zero_init` passes; the `py_contract_dump` N hashes equal the `test_smoke.py` constants.
- Python (0.4.0 wheel built from `0bb2272`, `ISO532_REQUIRE_PARITY=1`): 87 passed, 0 xfailed.

| `hash_gate.rs` `n_specific` | Round 1 | Round 2 (F-07) |
|---|---|---|
| windows scalar | `0x16937b45e6e4155d` | `0x80e89aeeafaf2164` |
| windows avx2 | `0x3d4b4b2df9073e48` | `0x38b0cdbd447978d7` |
| windows scalar mosqito_tail | `0xff98c57f3018ef94` | `0xb2247c2f9f943399` |
| windows avx2 mosqito_tail | `0x3f241da3fe334097` | `0xced0f74f725403e1` |
| linux scalar | `0x05dc55b516e20132` | `0x3065b74438e81ca6` |
| linux avx2 | `0x197c1084aab28c59` | `0xe510c9ec5b5244c3` |
| linux scalar mosqito_tail | `0x6e181dac593b5fef` | `0x062926a7788343e3` |
| linux avx2 mosqito_tail | `0x8213780cd5384fb0` | `0x10130ca6b26aa5af` |

## Independent verification (Astra, `fca4ccd`)

Delivered 2026-11-04 on commit `fca4ccd`, verdict **PARTIAL**: seven of nine items PASSED, no numeric or API release blocker. Report: [`verification/2026-11-04-release-0.4.0-fca4ccd/report.en.md`](verification/2026-11-04-release-0.4.0-fca4ccd/report.en.md) (brief: `verification/briefs/2026-11-04-release-0.4.0-acceptance.md`).

- Freeze: candidate / Round 1 / baseline built from git archives, 560 / 560 / 394 tracked files, byte-identical to the archives after execution.
- C golden: all 123 data files reproduce `tools/golden-c.sha256`; the official and single-cell sources match their hashes; the tool exits 1 on a wrong source.
- Gates: workspace 146 passed / 0 failed / 3 ignored; the wheel in a fresh venv with `ISO532_REQUIRE_PARITY=1`: 87 passed, 0 xfailed; fmt, both clippy gates, doc pairs, docs redaction and benchmark compilation pass; Linux lib 30, hash 1, contract dump 1 and CI subset 29 pass.
- F-04 to F-07 with an independent C wrapper and an external Rust program: signal 18 frame 1564 cell 36 = `nm[4]` = 0.8138793716641407, total bits `401fc356fc47a15a` as in Round 1; signal 23 frame 3893 total 4.7508434035893385; with only band 20 non-zero the total is 0.3999999999999986 (the binary64 result for the mathematical 0.4) and band 0 is all zero. Maximum differences of 13 series against the 0.24f C golden: total 2.712e-5, specific 2.100e-4; four tail points 8.99e-11 / 3.26e-23; all agree with the tables below.
- F-07 leaves total loudness unchanged: Round 1 (`2fc1708`) against `fca4ccd` on 24 Annex B WAVs plus the 3 s contract signal, 70,219 frames, `n` and `time_axis` bit differences 0; 16,902 specific cells change, all in the after-segment branch.
- Hashes: on Windows and Linux, all four scalar / AVX2 × zero / mosqito_tail sets of `n`, `n_specific` and `time_axis` equal the frozen values, with no CPU / UCRT allowance needed; the Windows wheel's Python N / time hashes also match.
- MoSQITo: time-varying total up to 3.94e-3, stationary 4.88e-4, both below 5e-3; the recorded specific values 3.147e-2 / 7.960e-3 reproduce.
- Contracts (PARTIAL): both versions pass 73,116 / 73,116 official Annex B reference points, minimum margin 0.0597 (signal 2, 1.0 Bark); custom-chunk streams of four signals give `n` and derived time bitwise equal to batch; seven grid lengths, nine DLL exports and the header equal v0.3.1. Gap: the public `StreamFrame` has no specific loudness, so the brief's stream-specific equality cannot be checked. This is an existing capability gap, not a regression.
- Record consistency (FAILED): the commit table omitted `5bbbb93`; it is added above. Versions, the CITATION exception, CHANGELOG, CI settings and all 54 numbers of the C tables match.

Diagnostic findings (not acceptance gates): on the same NL vectors, C without the `_ZUP` epsilon and with binary64 slope tables differs in total by 1.4e-14, but in specific loudness by 4.26, because nine float32 `ZK += 0.1f` steps give 0.9000000134110451 > 0.9 and cell ownership changes. Replacing only the grid with integer index / 10 brings the specific difference down to 1.3e-14. With all C constants in binary64 the end-to-end total difference is 5.9e-11, so no end-to-end 1.5e-14 claim is made. The C golden `meta.json` also differs from the frozen one in more than the date: both DLL hashes and the line endings of the substitution diff (CRLF versus LF); no data-file byte is affected.

Out of scope: F-03 authority, the stationary front end, performance measurement, release packaging, remote CI.

## Annex A C golden (D4 as revised / D-D, D-G)

- Reference program: the official `ISO_532-1.c` (SHA-256 `a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491`) with only `USL[12][4]` changed from `0.22f` to `0.24f` (substituted source SHA-256 `739af24dee118027cb419fcdb051d8b56b274211d986140d66d7ff4b9d52a7e9`); MSVC 19.44.35228 x64, `/O2 /fp:precise`; the wrapper only calls `f_loudness_from_signal` and `f_loudness_from_levels`. Round 2 did not change the C side; `data/golden-c/` is the Round 1 output.
- Three gate tiers: C-01 tail points, total and specific, 1e-10; whole series, total, 1e-4 sone; whole series, specific, 3e-4 sone/Bark (the post-F-07 measured maximum 2.100e-4 rounded up to one significant digit). The whole-series residue is the C program's `_ZUP += .0001f`, its float32 grid accumulation `ZK += 0.1f` and its other float32 literals (attribution in the diagnostics of "Independent verification").
- C-01 tail points (last output point of Annex B signals 18/23/24/25), identical before and after F-07:

| signal | Rust 0.4.0 − C golden (0.24f) | max specific diff | Rust 0.4.0 − unmodified C (0.22f) |
|---|---|---|---|
| 18 | −6.61e-11 | 9.1e-24 | −1.43e-8 |
| 23 | −5.16e-11 | 3.3e-23 | −1.28e-7 |
| 24 | −8.99e-11 | 2.2e-23 | −9.33e-9 |
| 25 | −7.41e-11 | 4.7e-24 | −7.41e-11 |

- Whole series (time-varying, Rust vs C golden 0.24f, default AVX2 dispatch):

| signal | max total diff (sone) | max specific diff (after F-07) | max specific diff (before F-07) |
|---|---:|---:|---:|
| sine_1k_60 | 1.471e-7 | 6.184e-5 | 3.582e-3 |
| sine_250_80 | 2.022e-5 | 2.100e-4 | 2.496e-3 |
| sine_4k_60 | 4.987e-8 | 8.214e-5 | 2.867e-3 |
| white_60 | 1.915e-6 | 6.235e-5 | 3.112e-2 |
| pulse_1k_70 | 1.465e-7 | 1.097e-4 | 1.287e-2 |
| step_60_80 | 1.645e-6 | 1.297e-4 | 2.209e-2 |
| annexb_sig3 | 1.472e-7 | 6.184e-5 | 3.527e-3 |
| annexb_sig5 | 2.712e-5 | 6.235e-5 | 3.147e-2 |
| annexb_sig10 | 9.795e-8 | 1.097e-4 | 3.842e-3 |
| annexb_c01_sig18 | 6.614e-6 | 9.397e-5 | 4.377e-2 |
| annexb_c01_sig23 | 3.248e-7 | 8.249e-5 | 3.508e-2 |
| annexb_c01_sig24 | 1.753e-6 | 6.217e-5 | 3.485e-2 |
| annexb_c01_sig25 | 7.781e-7 | 8.249e-5 | 2.639e-2 |

Stationary (main loudness + slopes on the C golden's levels, nine signals): total up to 1.530e-5 sone (annexb_sig5), specific up to 1.500e-4 sone/Bark (sine_250_80; 7.960e-3 before F-07). The total numbers are the same before and after F-07.

## Specific loudness against MoSQITo (D-H: recorded, not gated)

| source | maximum difference (sone/Bark) |
|---|---|
| Rust `golden_zwtv` (`NlInit::MosqitoTail`) | sine_1k_60 3.582e-3, pulse_1k_70 1.287e-2, step_60_80 2.209e-2, annexb_sig10 3.842e-3 |
| Rust `golden_zwst` (end to end) | sine_1k_60 6.3e-14, sine_250_80 3.922e-5, sine_4k_60 1.3e-14, white_60 1.8e-15, annexb_sig3 1.0e-14, annexb_sig5 7.960e-3 |
| Rust `golden_core` / `golden_zwst` (slopes only) | sine_250_80 3.922e-5, the other three 0 |
| Python parity, time-varying (mosqito_tail and default + silent tail give the same numbers) | sine_1k_60 3.582e-3, sine_250_80 2.496e-3, sine_4k_60 2.867e-3, white_60 3.112e-2, pulse_1k_70 1.287e-2, step_60_80 2.209e-2, annexb_sig3 3.527e-3, annexb_sig5 3.147e-2, annexb_sig10 3.842e-3 |
| Python parity, stationary | sine_250_80 3.922e-5, step_60_80 1.033e-3, annexb_sig5 7.960e-3, the other six ≤ 6.3e-14 |
| `tools/compare_mosqito.py`, 3 s | `nl_init="mosqito_tail"` 1.86e-3 (0.3.1: 3.46e-15); default 3.25e-2 (F-02 start, unchanged) |

Total loudness against MoSQITo keeps the 5e-3 sone gate; its numbers are the same before and after F-07.

## Round 1 findings, resolved

1. **Whole-series 1e-10 is not achievable.** Replaced by the three gate tiers of decision memo §7 (above). The 4.4e-2 specific difference was F-07, fixed in Round 2; the remaining ≤ 2.1e-4 is the C program's band-edge epsilon together with its float32 grid accumulation (independent diagnostics: both have to be replaced before the specific difference drops to the 1e-14 range).
2. **MoSQITo specific compatibility exceeds D-E.** Per D-H, specific loudness against MoSQITo is recorded, not gated; the two strict Python `xfail`s are removed.
3. **The Python `n` hash holds only on this Windows machine.** The CI py job now sets `HASH_GATE_DUMP_ONLY=1` on windows-latest, as the Rust job does.

## Not done / open

- Push, tag and GitHub CI follow the commit that records "Independent verification"; no release artifacts are built.
- The public `StreamFrame` carries no specific loudness (as in v0.3.1), so stream-versus-batch equality of specific loudness cannot be checked through the public API; the bitwise stream contract covers `n` and the time derived from the frame index.
- `CITATION.cff` still says 0.3.1: version and `date-released` were updated in the release commit in the past, and the release date is not known yet.
- The Round 2 RED commit `a1a261d` does not pass `clippy -D warnings` on its own (the 17-significant-digit test constants trigger `excessive_precision`); `0bb2272` adds the `#[allow]` and is clean again.
- F-03 (Table A.9) remains PENDING; the stationary front end is still undecided.
