# V-01 Annex B validator fail-closed: completion record

> 對照／Pair: [中文版](V01-ANNEXB-VALIDATOR-2026-10-31.zh-TW.md) · source: zh · synced 2026-11-01

Date: 2026-10-31 (Asia/Taipei). Base `d623d32` (v0.3.0 + the V-01 plan). Executed by Claude, authorised by the user ("push V-01 forward if it can be pushed"); followed `docs/superpowers/plans/phases/phase-v01-annexb-validator.md`, not handed to Codex. Test and documentation changes only; `iso532/src/` has zero diff.

## What changed

| File | Change |
|---|---|
| `iso532/tests/common/annexb_check.rs` (new) | `Verdict { Pass, Fail, Invalid }`, `InvalidReason`, `annexb_tolerance`, `annexb_verdict`; strict CSV reader `annexb_csv_path` / `annexb_csv`; `annexb_dir` |
| `iso532/tests/common/mod.rs` | exports `annexb_check`; `read_bin` split into `read_bin_path(&Path)`, same behaviour |
| `iso532/tests/annexb.rs` | additive `isoclose` removed; the three Annex B tests use `annexb_verdict` and print the `Verdict` on failure |
| `iso532/tests/annexb_validator.rs` (new) | 24 tests: tolerance rule 7, fail-closed 5, CSV 7, binary 5 |
| `README.md`, `README.zh-TW.md` | tolerance wording switched to the max rule, source stated as the workbook formula |
| `docs/ISO-ANNEXB-NUMERICAL-ERROR-2026-07-04.md` | one correction note added, historical numbers untouched |
| `CHANGELOG.md` | Unreleased → Changed |

## Gate results

| Gate | Result |
|---|---|
| `cargo fmt --all --check` | clean |
| `cargo clippy --all-targets -- -D warnings` (from `iso532/`, the CI command) | clean |
| `cargo clippy --workspace --all-targets --all-features -- -D warnings` | clean (the first run hit `invalid metadata` compile errors while the page file was full; the `-j 2` re-run passed; not a lint failure) |
| `REQUIRE_AVX2=1 cargo test --workspace --all-features` (`-j 3`) | all passed, 0 failed, 3 ignored (the existing hash dump, Python contract dump, silence throughput); includes `annexb` 3 and `annexb_validator` 24 |
| `git diff --stat iso532/src/` | empty |
| `tools/golden_manifest.py --verify` | 175 files match |

**The D1 risk did not materialise**: all three existing Annex B tests pass under the max rule, no new finding. This agrees with audit §11.5 (max rule, 0 exceptions over 25 cases).

## Deviations from the plan (reviewers: start here)

1. **Boundary literals.** The plan expected `ref=2.0, got=2.1 → Pass`. Under IEEE 754, `2.1 − 2.0 = 0.10000000000000009 > 0.1`, so the max rule fails it; the plan's expectation was wrong. Replaced by exactly representable offsets: `2.0625 → Pass`, `2.125 → Fail`; added `ref=8.0`: `8.375 → Pass`, `8.5 → Fail` (8.5 passes the additive rule exactly, a second control separating the formulas). The `ref=10.0, got=10.55` control from §6.1 and the `ref=0.0` / `ref=100.0` cases keep the plan's values; their floating-point behaviour was checked.
2. **Location of the CSV readers.** `annexb_csv` / `annexb_csv_path` live in `tests/common/annexb_check.rs`, not `annexb.rs`, because `annexb_validator.rs` needs them too. The name-based wrapper `annexb_csv(file)` is unchanged.
3. **BOM check.** Per D4 ("BOM only on the header line"), a data row containing `U+FEFF` panics; the plan listed no such negative test, one was added.
4. **239-row case.** The reader returns the 239 points it parsed; the test re-enacts the caller's `assert_eq!(len, 240)` under `catch_unwind` and checks that the message names 240.
5. **Module-level `#![allow(dead_code)]`.** `tests/common` is compiled into every test binary; binaries that do not use the verdict would see its public items as dead code, an error under `-D warnings`.
6. **Unit tests in a separate file** `annexb_validator.rs` (the plan allowed either placement). CI runs `cargo test`, which includes all integration tests.
7. Two small helpers, `Verdict::is_pass()` and `annexb_tolerance()`, are exposed for reuse by the future C-01 contract tests.

## Out of scope (untouched)

C-01 output length, C-02 non-finite input, the 1 % exception rule, the USL table, goldens, `data/`, the version number. The change sits in Unreleased; the user decides whether it ships with the next 0.3.x or with 0.4.0.

## Suggested follow-up

- Optional light review by Astra (test-only; the points to check are the D1 formula and the fail-closed list against audit §12.2 row V-01).
- This verdict is the tolerance check the C-01 "best option" (zero-padded C library reference) would use.

## Root cause of the floating-point boundary case (added 2026-11-01)

The user asked why the plan's case `ref=2.0, got=2.1 → Pass` had to be changed. Conclusion: **the verdict arithmetic is correct; the test literals are not exactly representable in IEEE 754, and real data sits far from the tolerance boundary.**

1. **Representation error of decimal literals.** `2.1` is stored in binary64 as `2.100000000000000088817841970012523…`, `0.1` as `0.1000000000000000055511151231257827…`, `2.0` exactly.
2. **The subtraction is exact.** `2.1 − 2.0` has operands within a factor of two (Sterbenz lemma), so no further rounding: the result is `0.100000000000000088817841970012523…`.
3. **The comparison.** The tolerance is `max(0.1, 0.05 × 2.0)`; `0.05 × 2.0` equals the stored `0.1` exactly, so the tolerance is `0.1000000000000000055…`. The difference exceeds it by `8.33e-17`, about 6 `ulp(0.1)` (`1.39e-17`). The verdict reports Fail as specified; that is correct behaviour.
4. **Why the plan was wrong.** It was written in decimal mental arithmetic; literals with fractional parts such as .1 or .05 are exactly the ones that round. Exactly representable offsets (`2.0625`, `2.125`) are used instead, and the remaining cases were checked with Python's `decimal` expansion: `10.55 − 10.0 = 0.5500000000000007` against tolerance `0.5` (fails as intended, margin 0.05); `105.0 − 100.0 = 5.0` is exact and `0.05 × 100.0` is exactly `5.0`, so it passes exactly on the boundary; `0.1 − 0.0` and the tolerance are the same literal.
5. **Effect on real verdicts: none.** Minimum margin (tolerance minus difference) over the three Annex B tests: signal 3 `N′` 0.0851 sone/Bark (Bark bin 66), signal 5 `N′` 0.0901, signal 10 `N(t)` 0.0998 sone (frame 77), signal 3 `N` 0.168, signal 5 `N` 0.445. The smallest margin is 6×10¹⁵ times `ulp(0.1)`; no representation error can flip it. The official workbook computes in Excel doubles and has the identical property; the verdict mirrors it.
6. **Decision: no epsilon.** D1 keeps the strict `≤`; an epsilon would depart from the workbook formula with no benefit. New test-writing rule: boundary cases use exactly representable values (`k/2ⁿ`) or sit on either side of the boundary with a margin of at least 1e-12.
