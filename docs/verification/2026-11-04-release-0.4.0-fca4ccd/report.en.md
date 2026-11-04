# Independent release 0.4.0 acceptance

Conclusion: **PARTIAL**. No numerical or API regression release blocker was found. The public streaming API never exposes specific loudness, so that requested proof remains unavailable; record consistency fails because the commit table omits one commit. These do not demonstrate a product regression, but the report must not be described as unconditional completion of all nine checks. No tag, push, commit, staging, or GitHub CI was performed.

Astra (`gpt-6-astra`), 2026-11-04 Asia/Taipei. `fca4ccda18a8fbada77031425e5e683f1acd5a8d` (`fca4ccd`).

| §2 | Status | Evidence |
|---|---|---|
| 1 | PASSED | [source-integrity.json](source-integrity.json) |
| 2 | PASSED | [golden-results.json](golden-results.json) |
| 3 | PASSED | [gates/gates-results.json](gates/gates-results.json) |
| 4 | PASSED | [numeric-results.json](numeric-results.json) |
| 5 | PASSED | [diagnostic-controls.json](diagnostic-controls.json) |
| 6 | PARTIAL | [contracts/contracts-results.json](contracts/contracts-results.json) |
| 7 | PASSED | [gates/gates-results.json](gates/gates-results.json) |
| 8 | PASSED | [gates/mosqito-measurements.json](gates/mosqito-measurements.json) |
| 9 | FAILED | [release-numeric-comparison.json](release-numeric-comparison.json) |

## 1. Freeze / 凍結

Built from git archives, not main. Candidate/Round 1/baseline have 560/560/394 tracked files, all byte-identical to their archives after execution. Main HEAD was `7900035c7ac318d789310fe817552a413c154b41`; initial tracked tree was clean and only this delivery became untracked. Source hashes are in [source-integrity.json](source-integrity.json). Rust/Cargo 1.99.1, Python 3.11.9, NumPy 2.4.6, maturin 1.14.1, MSVC 19.44.35228 x64 `/O2 /fp:precise`; complete Python packages and Linux toolchain are in gates logs.

## 2. C golden

All 123 binary files reproduce the frozen manifest exactly. The official source and single-cell variant hashes match the brief; the committed normalized diff matches. Wrong-source negative control exits 1. Finding: metadata differs in generation time, both DLL hashes and the substitution-diff hash (archive CRLF versus original generator-produced LF), not only the date. Original metadata hash matches the frozen manifest. This does not alter any data-file byte. See [golden-meta-differences.json](golden-meta-differences.json).

## 3. Gates

Workspace: 146 passed, 0 failed, 3 ignored. Fresh wheel/venv with `ISO532_REQUIRE_PARITY=1`: 87 passed, 0 xfailed. fmt, both clippy gates, focused tests, documentation pairs, docs redaction and benchmark compilation pass. Linux lib 30, hash 1, contract dump 1 and CI subset 29 pass. Initial environment failures (offline pip, undeclared matplotlib dependency, Docker pipe permissions) were repaired and rerun; they are retained separately from final product results.

## 4. F-04 / F-05 / F-06 / F-07

Independent C wrapper calls official entry points and external Rust CLI calls the frozen crate. SIG18 cell 36 equals nm[4] = 0.8138793716641407, cell 35 = 0.8201342464748338; total bits `401fc356fc47a15a` match Round 1. SIG23 total is 4.7508434035893385. Band-20-only total is 0.3999999999999986 (the binary64 computed result of `24.0-23.6`, within rounding error of mathematical 0.4); all first-band cells are zero. Across 13 sequences, total max 2.71180278250682250e-05, specific max 2.09972652732481890e-04; four tail maxima 8.98730629847466211e-11 and 3.25986050435033438e-23. Stationary nine-level-input maxima 1.52994289734920130e-05 and 1.50002845644259253e-04. All acceptance thresholds pass.

| Signal | N max | Specific max | Round 1 specific max |
|---|---:|---:|---:|
| annexb_c01_sig18 | 6.613789616e-06 | 9.396542937e-05 | 4.377285282e-02 |
| annexb_c01_sig23 | 3.248153462e-07 | 8.248619202e-05 | 3.508193084e-02 |
| annexb_c01_sig24 | 1.753251574e-06 | 6.217173584e-05 | 3.485164721e-02 |
| annexb_c01_sig25 | 7.781257789e-07 | 8.249086827e-05 | 2.639265176e-02 |
| annexb_sig10 | 9.794874511e-08 | 1.097084125e-04 | 3.842240067e-03 |
| annexb_sig3 | 1.471770910e-07 | 6.183566522e-05 | 3.526614607e-03 |
| annexb_sig5 | 2.711802783e-05 | 6.235161843e-05 | 3.147031276e-02 |
| pulse_1k_70 | 1.464543375e-07 | 1.097089178e-04 | 1.286871240e-02 |
| sine_1k_60 | 1.471443349e-07 | 6.183565230e-05 | 3.582281567e-03 |
| sine_250_80 | 2.022091941e-05 | 2.099726527e-04 | 2.495591954e-03 |
| sine_4k_60 | 4.987334279e-08 | 8.213898854e-05 | 2.867147115e-03 |
| step_60_80 | 1.645393574e-06 | 1.297287710e-04 | 2.208874236e-02 |
| white_60 | 1.915379471e-06 | 6.235281873e-05 | 3.111792681e-02 |

Round 1 versus candidate: 24 Annex B WAVs (signal 15 diffuse field) plus 3 s contract signal, 70219 frames; zero differing N/time bits. 16902 specific cells change, all inside the after-segment branch; zero outside. First ordered difference: signal 2, Bark cell 72/frame 5. Full coordinates and f64 hex are in numeric-results.json. Source-derived tracing is supporting localization evidence, not the independent C oracle.

## 5. Diagnostic / 診斷

Using identical Rust NL vectors, epsilon-zero/binary64-slope-table C has total max 1.42108547152020037e-14, reproducing the prior slope-stage claim (not a full-pipeline claim). Finding: specific max 4.25633562081179928e+00; removing epsilon changes sample ownership because 9 float32 0.1 increments give 0.9000000134110451 > 0.9. Replacing only grid accumulation with integer-index/10 in a diagnostic control reduces specific max to 1.26565424807267846e-14, without changing total. Making all C constants binary64 yields full-pipeline total max 5.91793281046193442e-11; it does not prove 1.5e-14 end-to-end. Diffs, coordinates and hashes are delivered. None of these diagnostic variants replaces the authorized 0.24f reference.

## 6. Contracts / 契約

Both versions pass 73,116/73,116 official reference points, with minimum margin 0.059702781183555126 (signal 2, specific 1.0 Bark, worksheet G17). Four chunked signals, 4,136 frames per version, have zero N and derived-time bit differences. Seven grid lengths and all nine DLL exports match; headers are byte-identical. Supplemental FFI panic tests pass 17/17 and C smoke passes. cbindgen 0.29.4 regeneration differs in line endings only and is identical after LF normalization. Finding/gap: both public StreamFrame versions expose no specific loudness and no floating time_axis; time is derived from the frame index. Public stream-specific equality cannot be tested. This pre-existing capability gap is not a regression or independent release blocker. Workbook derived Nmax/N5 summaries are outside the reference-point count.

## 7. Hashes / 雜湊

All four Windows and four Linux scalar/AVX2 × zero/mosqito_tail N/specific/time tuples equal frozen platform constants exactly. Windows wheel Python N hashes and time also match. Four Windows Round 1 specific hashes were rerun in a separate target and match the old release table; an initial shared-target cache result was rejected as invalid evidence. No CPU/UCRT allowance was needed. Exact expected/observed hex values are in gates-results.json.

## 8. MoSQITo

Compatibility only, not correctness authority. Across nine fixtures: time-varying total max 3.94196712451133635e-03, stationary total max 4.88005984661032954e-04, both below 5e-3. Specific maxima 3.14702989925296772e-02 (time-varying annexb_sig5) and 7.95965803937281891e-03 (stationary annexb_sig5) reproduce the record; specific has no acceptance threshold.

## 9. Record consistency / 紀錄一致性

Versions, CITATION exception, changelog markers and CI py hash setting match. All 54 C-table numeric entries (including Round 1 and stationary values) match printed rounding. Gate counts and frozen hashes reproduce. Finding: release commit table represents 11 of 12 commits and omits `5bbbb93228b9972c0277415bebd565364de974fc`; therefore this item is FAILED. Also correct metadata-only-date wording and avoid claiming unavailable public stream-specific proof. Historical RED-run provenance and prior Linux runs are not recreated as historical events; current candidate/isolated Round 1/Linux evidence is supplied. This is a documentation finding, not evidence of a numeric defect.

## Delivery and limits

See [replay.md](replay.md), [delivery-check.md](delivery-check.md) and [delivery-integrity.json](delivery-integrity.json). The manifest hashes redacted delivered bytes and excludes itself. Original source/input/binary hashes retain their original meaning. F-03 authority, stationary front-end validation, performance measurement, release packaging and remote CI are outside scope. Correct record wording before using this report to update the release acceptance section; retain the explicit streaming gap.
