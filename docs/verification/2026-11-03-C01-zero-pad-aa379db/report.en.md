# C-01 independent verification report

Date: 2026-11-03 (Asia/Taipei). Verifier: Astra. Tested commit: `aa379db8f3dc37f5048ac6c8b7a6d4ba2a6c3b76` (`aa379db`). Pair: [Traditional Chinese](report.md).

## 1. Decision

**PARTIAL — do not close this round's C-01 numerical gap.** The independent official-C references were obtained. All 960 target specific-loudness comparisons satisfy <=1e-14 sone/Bark, but all 4 total-loudness differences exceed <=1e-14 sone. Each combined point is therefore **WITHIN TOLERANCE**, not AGREES. The largest total difference is 4.1705202592388566e-7 sone. The Annex B fallback `max(0.1,0.05*abs(reference))` passes but does not replace the preregistered gate.

Nine of ten final gates pass; the four-rounding-agreements gate fails. Required inputs/builds/precision were obtainable: **blocked: none**. **Skipped:** full workspace/binding/package/performance acceptance and a separate all-requirements audit closure review. The 7 output-grid tests are supporting evidence, not comprehensive reset/flush/short-input acceptance. No DSP, test, golden, decision memo, brief or audit closure row was changed; no commit/push.

## 2. Frozen material and execution

The bilingual [preregistered design](experiment-design.en.md) was written before execution. `run-start.json` records start `2026-11-03T00:18:45.230682+00:00` and both design hashes; the designs remained unchanged. Primary execution finished `2026-11-03T00:25:01.520303+00:00`. The source was extracted from the fixed commit into isolated scratch; archived source hashes before/after match. The pre-existing untracked F-03 delivery was preserved.

Official archive material was recovered from the retained local evidence ZIP and rebuilt this round; prior numbers were not reused. `ISO_532-1.c` is unchanged, SHA-256 `a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491`. The original header, CLI main/helper and archive hashes are in the inventory. MSVC 19.44.35228 x64 used `/nologo /O2 /fp:precise`; `_CRT_SECURE_NO_WARNINGS` only suppresses CRT diagnostics. Rust used `rustc 1.99.1 (58cf8f9c3 2026-10-13)`, release profile and default runtime dispatch (AVX2 available). The Rust harness has a separate Cargo manifest/lock and calls the fixed snapshot's public `loudness_zwtv`.

All WAVs are mono 48 kHz signed PCM16 little-endian. Decode integer/32768, calibrate using the official Annex C 60 dB file and the CLI-equivalent sequential accumulation. The pressure multiplier is **2.8357977163914438**, bits `4006afb6b68fc829`. C and Rust use identical little-endian binary64 pressure bytes; the C helper/CLI-equivalent decoder produces identical bytes for every padded and boundary WAV. Padding only appends zeros. Original WAV, decoded PCM, pressure, padded WAV/pressure and calibration hashes are retained. `decoder-wrapper.c.txt` changes no DSP body: it calls the official reader and exports calibrated inputs. `rust-probe.rs.txt` exports full arrays and prints the target bits.

The C/CLI build and all computational subprocesses exited 0. `cl /Bv` without source exited 2 with D8003 as an expected version query; the environment's `vswhere.exe` lookup warning was retained and was nonfatal. Neither is hidden as a numerical pass.

| Binary | SHA-256 |
|---|---|
| c01-probe.exe | f9a538f6c346e59c36ed6f8e9da1bafa9ad1072855b2fc4f5fc65b6e33a5e256 |
| reference.dll | fb1ef5be897b1230b6c0aae62fae125b64a9d7080ee00d70cc59b134086a7e5d |
| reference_cli.exe | 598b224790d6c7c28ed16e95ce4e2d8f01973f2380f67451d2df5bf226f6d854 |


## 3. Target points and primary findings

Zero-based indexing: K=floor(L/24), L_pad=96*(ceil(L/96)+1), j=K/4=Rust frames-1. Reference values are undecimated padded C frame K before CLI serialization. All full arrays had the expected shapes and finite values before comparison. Each total and all 240 specific values have decimal17 and binary64 bits in JSON/CSV. The output times are exact Rust grid values; decimal representations below retain binary64 precision.

| Signal | L | K | L_pad | j | Rust frames | t (s) |
|---|---|---|---|---|---|---|
| 18 | 103969 | 4332 | 104160 | 1083 | 1084 | 2.1659999999999999 |
| 23 | 122401 | 5100 | 122592 | 1275 | 1276 | 2.5499999999999998 |
| 24 | 115202 | 4800 | 115392 | 1200 | 1201 | 2.3999999999999999 |
| 25 | 122401 | 5100 | 122592 | 1275 | 1276 | 2.5499999999999998 |

| Signal | C total (sone) | Rust total (sone) | Total abs diff | Max specific abs diff | Verdict |
|---|---|---|---|---|---|
| 18 | 0.00095543263901191108 | 0.00095521696145359593 | 2.1567755831514244e-07 | 9.1113381304915761e-24 | WITHIN TOLERANCE |
| 23 | 0.0034913530909121875 | 0.0034909360388862636 | 4.1705202592388566e-07 | 3.2598605043503344e-23 | WITHIN TOLERANCE |
| 24 | 0.0010659327175432183 | 0.0010656334112001788 | 2.9930634303952305e-07 | 2.1604372979486025e-23 | WITHIN TOLERANCE |
| 25 | 0.0011947790020081512 | 0.0011945761670982473 | 2.0283490990394455e-07 | 4.6742163950249433e-24 | WITHIN TOLERANCE |


The specific column is a maximum over all 240 Bark values, not a selected subset. All 4 totals fail the rounding gate; all 960 specific values pass. CLI total and specific data row j existed, had the expected time and 240 specific columns, and matched four-decimal serialization within 0.000050000001. CLI text did not supply the high-precision references.

## 4. Controls and final gates

All 19,332 original internal total frames and 4,639,680 specific values are bitwise identical between original and padded C runs, including unsampled internal frames. These are measured comparisons, not a CLI-grid inference.

| Signal | C total comparisons | C specific comparisons | Bitwise mismatches (total/spec) | Max abs diff (total/spec) | First mismatch |
|---|---|---|---|---|---|
| 18 | 4332 | 1039680 | 0 / 0 | 0 / 0 | none |
| 23 | 5100 | 1224000 | 0 / 0 | 0 / 0 | none |
| 24 | 4800 | 1152000 | 0 / 0 | 0 / 0 | none |
| 25 | 5100 | 1224000 | 0 / 0 | 0 / 0 | none |


Comparator control: the first attempt compared an injected reference copy against Rust. Because the real total discrepancy was already above threshold, its first reported failure was total, confounding the intended coordinate check. The entire original result and original runner are preserved. The correction compares the original C reference with its +1e-6 copy at `specific[137]` using the **same unchanged comparator**. All 4 baseline self-comparisons return AGREES; all 4 injected comparisons return non-AGREES and exactly that coordinate. Finite/shape rejection controls also pass. No original numerical values or thresholds changed. The corrected reproduction runner is delivered; only this isolated control was rerun, with timestamps and before/after harness hashes in `control-correction.json`.

| Gate | Status |
|---|---|
| official_source_identity | passed |
| source_snapshot_unchanged | passed |
| four_rounding_agreements | failed |
| all_internal_prefix_invariance | passed |
| comparator_negative_control | passed |
| finite_shape_rejection_controls | passed |
| CLI_target_serialization_grid | passed |
| eight_boundary_rows | passed |
| identical_pressure_input | passed |
| supporting_output_grid_contract | passed |


The fixed snapshot's `cargo test -p iso532 --test output_grid --locked --offline` passed **7/7** (0 failed, 0 ignored), including 16 length cases, time grid, zero-padding/real-continuation prefix determinism and stream chunking. Its compiler log and exit code are retained.

## 5. Length-boundary measurements

Base: Annex B 18 first 4897 calibrated samples, hashed in `boundary_base`; each row is an exact prefix. C library counts are actual returns, CLI counts are parsed data rows, Rust counts are loaded output-array lengths. Every row matches the preregistered table.

| L | C frames | CLI total | CLI specific | Rust n | Rust spec elements | Rust time | Status |
|---|---|---|---|---|---|---|---|
| 4800 | 200 | 50 | 50 | 50 | 12000 | 50 | passed |
| 4801 | 200 | 50 | 50 | 51 | 12240 | 51 | passed |
| 4823 | 200 | 50 | 50 | 51 | 12240 | 51 | passed |
| 4824 | 201 | 50 | 51 | 51 | 12240 | 51 | passed |
| 4825 | 201 | 50 | 51 | 51 | 12240 | 51 | passed |
| 4895 | 203 | 50 | 51 | 51 | 12240 | 51 | passed |
| 4896 | 204 | 51 | 51 | 51 | 12240 | 51 | passed |
| 4897 | 204 | 51 | 51 | 52 | 12480 | 52 | passed |


## 6. Findings and current interpretation

The supplementary read-only diagnostic confirms that C/Rust total differences already exceed 1e-14 at common output **j=54 (0.108 s)** for every signal, well before the added tail point. Rust original versus padded outputs are bitwise equal for **all original total and specific values, including the target**. Combined with the C invariance control, the observed cross-implementation difference is not introduced by this padding operation.

| Signal | Common points | First total diff >1e-14 (j) | Max common total abs diff | Max common specific abs diff | Rust original/padded total/spec mismatches |
|---|---|---|---|---|---|
| 18 | 1083 | 54 | 0.0030368413726424848 | 0.043772852817229202 | 0 / 0 |
| 23 | 1275 | 54 | 0.0015480181402631743 | 0.035081930844496512 | 0 / 0 |
| 24 | 1200 | 54 | 0.0034863683542534218 | 0.034851647205261127 | 0 / 0 |
| 25 | 1275 | 54 | 0.0006434225633227264 | 0.026392651762537689 | 0 / 0 |


Source evidence: official C `ISO_532-1.c:1002-1015` computes slope total/specific then applies temporal weighting to total only; `:553-574` carries low-pass state and `:607-614` combines 3.5 ms/70 ms branches. The fixed Rust `iso532/src/zwtv/mod.rs:130-150` and `temporal_weighting.rs:40-55` do the corresponding separation and carry historical state. Thus a nearly vanished final specific spectrum can agree while weighted total still reflects earlier differences. This is a supported interpretation of the state structure; **the upstream numerical root cause is not isolated**, and no F-03 coefficient attribution is made. There are also earlier specific differences, reported separately in the diagnostic.

The decision memo's extension from within-implementation prefix determinism to 1e-14 cross-implementation total agreement was a hypothesis; this run does **not** confirm it. Keeping ceil and obtaining valid padded references are supported here; closing the stricter numerical gate is not. A future separate stage-by-stage investigation would need matched pre-weighting total histories and temporal-weighting outputs before identifying a cause or proposing a change. This report does not amend the existing decision or audit row.

## 7. Evidence, reproduction and limits

- [results.json](results.json): final results, all 241 C/Rust values per signal, bits/decimal17, both controls, input/output hashes, boundaries and gates.
- `signal-*-target.csv`: 964 value pairs with round-trip decimal17 and binary64 bits. `*-Loudness.csv` / `*-SpecLoudness.csv`: original CLI serialization.
- [run-start.json](run-start.json), [run-log.json](run-log.json): preregistration hashes, commands, versions, stdout/stderr, exit codes and library return values.
- [attempt-1-results.json](attempt-1-results.json), [attempt-1-run_experiment.py.txt](attempt-1-run_experiment.py.txt), [control-correction.json](control-correction.json), [control-correction.diff.txt](control-correction.diff.txt): original attempt and explicit comparator-control correction.
- [history-diagnostic.json](history-diagnostic.json), [diagnose_history.py](diagnose_history.py): same-round follow-up, separate from primary acceptance.
- [source-input-hashes.json](source-input-hashes.json), [delivery-check.md](delivery-check.md), [delivery-integrity.json](delivery-integrity.json): material provenance and post-redaction integrity.

Use [commands.md](commands.md) and the delivered scripts to repeat in new scratch/output directories with the inventoried original material. Only UTF-8 text is delivered; WAVs/binaries/full raw arrays remain in scratch and are identified by hashes. Harness hashes recorded before redaction identify the executed originals; final deliverable hashes identify redacted text and do not claim byte identity with those originals. `delivery-integrity.json` explicitly excludes itself.

This is numerical verification on the stated snapshot/toolchain and four signals plus eight shape controls. It is not general ISO certification, an independent F-03 resolution, cross-platform validation or a full C-01 audit closure. The failed strict total gate remains open.
