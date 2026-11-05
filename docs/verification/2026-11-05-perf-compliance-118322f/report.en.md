# v0.4.0 performance and standard-conformance check

> 對照／Pair: [中文版](report.md) · source: zh · synced 2026-11-05

Claude (Opus 5.5, main agent, not Astra), 2026-11-05 Asia/Taipei. Tested: `v0.4.0` = `118322f8300dc752f1d38a79db230a2db5ff2870` (crate sources identical to `fca4ccd`, the snapshot Astra accepted); baseline: `v0.3.1` = `aa379db8f3dc37f5048ac6c8b7a6d4ba2a6c3b76`.

## Conclusions

- **Performance: 0.4.0 causes no measurable end-to-end regression.** Only `calc_slopes` changed; that stage alone is 6% to 12% slower with specific loudness and 0% to 4% slower for total loudness only. The interleaved end-to-end Criterion A/B moves by −1.9% to +5.4%, the same order as the round-to-round noise (about ±4%); the one consistent signal is +2.0% / +2.2% for single-thread batch. Through the Python binding, the 3-second run has the same median for both versions (13.9–14.2 ms).
- **The README performance tables were stale**, mainly because of the machine state, not 0.4.0: on the same machine MoSQITo also went from 6.68 s to 7.23 s (+8%). The README is updated with the 2026-11-05 measurement.
- **Standard conformance: for all 25 ISO 532-1 Annex B test signals and their 73,116 workbook reference points, both 0.4.0 and 0.3.1 have 0 points outside the per-point tolerance**; minimum margin 0.0597 sone/Bark (signal 2, 1.0 Bark). This was recomputed with an independently rewritten comparator and matches the 2026-11-04 Astra round.
- **New summary values:** Nmax and N5 (workbook formula) of the 20 time-varying signals are all within max(0.1, 5%), with a consistent bias of +0.14% to +0.18%; 0.4.0 differs from 0.3.1 by ≤ 7e-4 sone. The workbook sets no tolerance for Nmax / N5, so these are diagnostics, not a PASS.
- **Limits of the conformance claim:** the per-point Annex B rule gives a PASS. The formal N5 definition and the "exactly 1%" exception rule remain UNRESOLVED; `USL[12][4]` (F-03) remains PENDING; the full text of the standard has not been obtained. **"Fully conforms to ISO 532-1" cannot be claimed**; the supported statement is "passes the per-point criterion of the Annex B workbooks".

## 1. Scope and method

- Each tag was checked out with `git worktree add --detach` under the gitignored `tmp/`, each with its own `CARGO_TARGET_DIR`. The main working tree and the project `.venv` were not modified.
- Python measurements used two fresh venvs with one wheel each (`--no-deps --no-index`); numpy, mosqito, pytest and openpyxl were borrowed from `.venv` through a `.pth` file.
- Annex B inputs are the `sig1..25.bin` files decoded and calibrated in the 2026-11-04 Astra round; their SHA-256 was re-checked against that round's `contracts-results.json`.
- Environment: AMD Ryzen 5 3600 (12 logical processors), 64 GB, Windows 10 Pro 19045, power plan Balanced; rustc 1.99.1, Criterion 0.5.1, rayon 1.12.0, Python 3.11.9, NumPy 2.4.6, MoSQITo 1.2.1. See [environment.json](environment.json).

## 2. Release artifacts (built from `v0.4.0`)

| file | SHA-256 |
|---|---|
| `iso532-0.4.0-cp39-abi3-win_amd64.whl` | `724b272c86ee35b27a51852674538adeeb1979143364de89c59b5476ad244cc0` |
| `iso532_ffi.dll` | `11a126257863df923e8ae41108fddb570f3f30a2bee0ed3be8c73b688d4ceb28` |
| `iso532_ffi.dll.lib` | `e5b7a8f812cd9e6d8be7a22f15dd0493ef3ebda7920757f3858d1e63026c05a9` |
| `iso532.h` | `0f548fd348cb0e3999ce8892bec05d4a5afd53740eb695428ad0eca9a45b709b` |

- `cargo build --locked --release -p iso532-ffi`; `maturin build --release --locked` (maturin 1.14.1).
- `iso532.h` is the tag's Git blob as stored, byte-identical to the header published with 0.3.1; the import library is also byte-identical to 0.3.1 (exports unchanged). The header from the worktree checkout has CRLF through autocrlf and was not used.
- The wheel METADATA says `Version: 0.4.0`; in a fresh venv with `ISO532_REQUIRE_PARITY=1`, `iso532-py/tests` gives 87 passed ([pytest-wheel-v0.4.0.log](pytest-wheel-v0.4.0.log)).
- The DLL and wheel embed build information; a rebuild on another machine is not expected to reproduce their hashes. The antivirus scan (the build machine runs Avira) has not been done and is left as a manual step. The artifacts were not uploaded.

## 3. Performance

### 3.1 The `calc_slopes` stage

[slopes_harness.rs.txt](slopes_harness.rs.txt) is compiled against each version as a path dependency, builds 274,860 21-band core loudness vectors from Annex B signals 2–25, repeats each timing 30 times and runs three interleaved rounds ([slopes-stage.log](slopes-stage.log)). The inputs come from main loudness before nonlinear decay, so the F-05 branch fires at a somewhat different rate than in the full pipeline.

| per vector (ns, median of three rounds) | v0.3.1 | v0.4.0 | change |
|---|---:|---:|---:|
| `calc_slopes` (with 240 specific cells, batch path) | 4614 / 4743 / 4719 | 4873 / 5129 / 5277 | +5.6% to +11.8% |
| `calc_slopes_n_only` (total only, stream path) | 4503 / 4593 / 4582 | 4508 / 4715 / 4779 | +0.1% to +4.3% |

The two versions have different checksums, each stable across rounds.

### 3.2 End-to-end Criterion (10 s, 480,000 samples, 5,000 output frames)

[criterion/run_criterion.sh](criterion/run_criterion.sh) runs three interleaved rounds, v0.3.1 then v0.4.0 in each; values are the median over rounds of the Criterion point estimate ([criterion/criterion-summary.json](criterion/criterion-summary.json)).

| workload | v0.3.1 (ms) | v0.4.0 (ms) | change | round range v0.3.1 / v0.4.0 |
|---|---:|---:|---:|---|
| ZWTV batch, 12 threads, scalar | 63.187 | 66.577 | +5.4% | 62.9–66.8 / 63.6–67.3 |
| ZWTV batch, 12 threads, AVX2 | 49.155 | 48.898 | −0.5% | 46.2–50.6 / 48.5–49.6 |
| ZWTV batch, 1 thread, scalar | 351.350 | 358.990 | +2.2% | 351.2–355.1 / 352.3–361.8 |
| ZWTV batch, 1 thread, AVX2 | 248.890 | 253.880 | +2.0% | 248.3–259.2 / 251.2–266.7 |
| stream 480-sample chunks, scalar (`RAYON_NUM_THREADS=1`) | 340.820 | 334.320 | −1.9% | 326.4–347.8 / 331.3–350.2 |
| stream 480-sample chunks, AVX2 (`RAYON_NUM_THREADS=1`) | 228.080 | 239.690 | +5.1% | 223.7–233.4 / 231.0–242.3 |
| stream, scalar (default threads) | 320.650 | 333.960 | +4.2% | 320.6–346.9 / 330.9–344.2 |
| stream, AVX2 (default threads) | 232.920 | 233.850 | +0.4% | 225.2–236.6 / 226.1–238.8 |
| filter bank, 12 threads, scalar | 15.348 | 15.329 | −0.1% | — |
| filter bank, 12 threads, AVX2 | 5.610 | 5.572 | −0.7% | — |

Reading: the stream is single-threaded, so both thread settings run the same workload, yet they give +5.1% and +0.4%; changes within ±5% are mostly noise. The filter bank did not change and stays within ±1%, which makes it a control. Single-thread batch is +2% on both backends, consistent with the slower slope stage of 3.1: batch calls `calc_slopes_into` once and `calc_slopes_n_only` three times per four internal (2 kHz) frames (`iso532/src/zwtv/mod.rs:129-134`), about 5,000 plus 15,000 calls for a 10 s input; the increments of 3.1 predict about +3 ms (+1.3%), the same order as the measured +5 ms (+2%). The stream only calls `n_only`; the predicted +2 ms (+1%) lies within the noise.

### 3.3 Python binding and MoSQITo (3 s signal)

- `tools/compare_mosqito.py` (0.4.0 wheel, 30 runs): ISO532 binding mean 14.963 ms (SD 1.262), MoSQITo 7.233612 s (SD 0.186382), relative speed 483.44x. The differences equal the README values: with the default `nl_init="zero"`, `N(t)` 5.81e-3 sone and `N_specific(t)` 3.25e-2 sone/Bark (F-02 start). See [compare-mosqito-v0.4.0.log](compare-mosqito-v0.4.0.log).
- Interleaved binding A/B ([binding_ab.py](binding_ab.py), 3 rounds × 30 runs): means v0.3.1 13.99 / 14.78 / 14.14 ms, v0.4.0 14.02 / 14.28 / 15.03 ms; medians 13.90 / 14.41 / 14.16 against 13.90 / 14.08 / 13.95 ms. No difference is visible.

### 3.4 Against the README baselines of 2026-07

| item | README baseline | 2026-11-05 (v0.4.0) |
|---|---:|---:|
| ZWTV batch 12 threads scalar / AVX2 (2026-07-10) | 142.224 / 47.461 ms | 66.577 / 48.898 ms |
| ZWTV batch 1 thread scalar / AVX2 (2026-07-21, `8fde6b6`) | 351.460 / 275.410 ms | 358.990 / 253.880 ms |
| stream scalar / AVX2 (2026-07-21) | 360.930 / 233.420 ms | 334.320 / 239.690 ms |
| 3 s binding / MoSQITo (2026-07-20) | 12.449 ms / 6.681 s | 14.963 ms / 7.234 s |

The large drop of 12-thread scalar comes from other changes after July, not from 0.4.0. MoSQITo slowed down together with the binding (about 8% to 20%), while the binding version A/B shows no difference, so the change of the 3-second row is the machine state.

## 4. Standard conformance (ISO 532-1:2017 Annex B)

### 4.1 Per-point rule

The rule is `|got − ref| ≤ max(0.1, 0.05·|ref|)`, read from the official Annex B workbooks (V-01). Stationary signals compare total loudness and 240 specific cells; time-varying signals compare N(t) at every workbook time point, and signals 6–13 also the N′(t) curve at the Bark value named in the workbook. Signal 15 is diffuse field, the others free field. Script: [compliance.py](compliance.py).

| workbook | signals | reference points | outside | minimum margin (location) |
|---|---|---:|---:|---|
| B.2 stationary (third-octave level input) | 1 | 241 | 0 | 0.0999 (N′, index 226) |
| B.3 stationary synthetic signals | 2–5 | 964 | 0 | 0.0597 (signal 2, N′ 1.0 Bark) |
| B.4 time-varying synthetic signals | 6–13 | 46,400 | 0 | 0.0952 (signal 9, N(t)) |
| B.5 time-varying technical signals | 14–25 | 25,511 | 0 | 0.0954 (signal 17, N(t)) |
| total | 1–25 | 73,116 | 0 | 0.0597 |

v0.3.1 gives exactly the same result. The wheel outputs recomputed for signals 2–25 are bitwise equal to the Astra Rust outputs (both versions); signal 1 has no Python entry point, so the Astra Rust output is reused after checking its hash.

### 4.2 Nmax and N5 (diagnostics)

Workbook cell B5 holds Nmax and B6 computes N5 with `PERCENTILE(…, 0.95)`, but no tolerance is set for either. The same statistics were computed from our N(t) over the row range of each workbook formula and compared on the max(0.1, 5%) scale as a diagnostic. The cached workbook N5 equals my formula recomputation for 20 / 20 signals, and every Nmax equals the maximum of the reference N column.

- Nmax: all 20 signals within the scale, bias +0.140% to +0.170%, largest absolute difference +0.054 sone (signal 16, reference 38.536), minimum margin 0.208 (signal 10).
- N5 (workbook definition): all within the scale, bias +0.139% to +0.176%, minimum margin 0.099 (signal 10).
- For signals 12 and 13 the N5 formula references column E (the lower 5% bound), not the N column; following the workbook, the same transform is applied to our N before comparing. This formula oddity was already noted in `docs/修正報告2.md` §11.6 and is recorded unchanged.
- With the official CLI definition of N5 (whole output, mean of the sorted values at ⌊0.95n⌋ and the one before), the difference to the workbook value reaches 0.416 sone (signal 12). This is the difference between the two definitions, not an engine error.
- 0.4.0 against 0.3.1: Nmax differs by at most 7.0e-4 sone (signal 14), N5 by at most 6.8e-4 sone (signal 20).

Nmax and N5 of every time-varying signal are consistently about 0.15% high, the same tendency as the per-point comparison; this is far inside the tolerance but worth recording for any later investigation of its source (for example filters or calibration).

### 4.3 Conformance status

| item | status | basis |
|---|---|---|
| Annex B per-point rule, 25 signals | **PASS** (0 / 73,116) | 4.1; same as Astra 2026-11-04 |
| Nmax and N5 summary values | diagnostic: all within max(0.1, 5%) | 4.2; the workbook sets no tolerance |
| Formal N5 definition | UNRESOLVED | workbook and CLI definitions differ; signals 12/13 reference column E; `docs/修正報告2.md` §11.6, §15.5 |
| "Exactly 1%" exception rule | UNRESOLVED, not exercised | no point is outside, so no exception is needed |
| Against the official Annex A C program (`USL[12][4]` = 0.24f) | PASS (0.4.0 acceptance gates) | tail points 9.0e-11, whole series 2.7e-5 / 2.1e-4; Astra 2026-11-04 |
| `USL[12][4]` (Table A.9, F-03) | PENDING | the 2017-11 correction did change Table A.9, but which cell is unknown; `docs/F03-USL12-4-STATUS-2026-10-31.md` |
| Stationary front end | MoSQITo-compatible spectrum path by design, undecided | signals 3/5 deviate by +0.82% / −0.76%, within tolerance |
| Full text of the standard | not obtained | the per-point rule comes from the workbooks, not a clause-by-clause check |

## 5. Limits

- One machine, one session; interleaving cancels slow drift but not short bursts of background load.
- The stage harness feeds core loudness before nonlinear decay.
- No performance measurement on Linux; artifacts are built for Windows x64 only.
- The conformance part reuses the inputs decoded by Astra instead of decoding the WAVs again; the input hashes were checked.

## 6. Evidence files

| file | content |
|---|---|
| [environment.json](environment.json) | tested commits, host, toolchain, wheel hashes |
| [artifacts-SHA256SUMS.txt](artifacts-SHA256SUMS.txt) | SHA-256 of the four artifacts |
| [pytest-wheel-v0.4.0.log](pytest-wheel-v0.4.0.log) | Python tests on the 0.4.0 wheel |
| [slopes_harness.rs.txt](slopes_harness.rs.txt), [slopes-stage.log](slopes-stage.log) | `calc_slopes` stage timing |
| [criterion/](criterion/) | runner, summariser, 12 Criterion logs, summary JSON |
| [binding_ab.py](binding_ab.py), [binding-ab.log](binding-ab.log) | interleaved binding A/B |
| [compare-mosqito-v0.4.0.log](compare-mosqito-v0.4.0.log) | the README 3 s MoSQITo comparison |
| [compliance.py](compliance.py), [compliance-v0.4.0.json](compliance-v0.4.0.json), [compliance-v0.3.1.json](compliance-v0.3.1.json) | Annex B per-point, Nmax / N5, cross-checks |
| [delivery-integrity.json](delivery-integrity.json) | SHA-256 of each file after redaction (excluding itself) |

Builds, WAVs, wheels, DLLs and worktrees stay in `tmp/` and are not committed.
