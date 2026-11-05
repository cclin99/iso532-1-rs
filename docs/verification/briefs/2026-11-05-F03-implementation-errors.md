# Verification brief: implementation errors against Annex B and the contribution of `USL[12][4]`

> 對照／Pair: [中文版](2026-11-05-F03-implementation-errors.zh-TW.md) · source: zh · synced 2026-11-05

To: Astra (`gpt-6-astra`). Issued 2026-11-05 (Asia/Taipei) by the main agent at the user's request; the main agent runs a separate round at the same time, and neither refers to the other. Verification round; no code change.

## 1. Question

`USL[12][4]` of ISO 532-1:2017 (upper-slope table, row 13, column 5, zero-based) has two values across implementations: `0.22f` in the official Annex A C program; 0.24 in MoSQITo 1.2.1, SQAT and this project's `iso532` 0.4.0. Measure independently:

1. The error of the official C program, SQAT, MoSQITo and `iso532` against the Annex B workbook reference values.
2. How much of it comes from this cell: run every implementation once with its own value and once with only this cell set to the other value.
3. Whether the main agent's claim in [`docs/verification/2026-11-05-F03-workbook-provenance-118322f/`](../2026-11-05-F03-workbook-provenance-118322f/report.en.md) holds: the Annex B workbooks were produced by the unmodified official C program (0.22f) with the conversion "full scale 1.0 = 2√2 Pa"; of the 12,287 points where the two official C builds differ by ≥ 2e-4 sone, the workbook equals the 0.22 build at 11,174 points and the 0.24 build at 0.

Background (you may read it, but every number must be reproduced yourself; do not reuse the main agent's output files):
- Conversion convention: [`2026-11-05-annexb-bias-118322f/`](../2026-11-05-annexb-bias-118322f/report.en.md). The calibration file is 0.0226 dB below its stated 60 dB; converting with it makes loudness consistently about 0.15% high.
- ZWST front end: [`2026-11-05-zwst-root-cause-118322f/`](../2026-11-05-zwst-root-cause-118322f/report.en.md).
- Earlier F-03 rounds: `docs/F03-USL12-4-STATUS-2026-10-31.md`.

## 2. Scope

1. **Freeze.** The snapshot under test is `493fd59` (the `iso532` crate is byte-identical to `v0.4.0` = `118322f`); build from an isolated checkout (`git worktree add` or `git archive`), not the main working tree. Record the toolchain: rustc, Python, NumPy, SciPy, MSVC, and the MATLAB or Octave version.
2. **Official material.** The ISO files are in `tmp/c01-material/official/`. Record the SHA-256 of each: `ISO_532-1.c` (expected `a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491`), `ISO_532-1_main.c`, `ISO_532-1_helper.c`, the three workbooks, the 24 WAVs, `Test signal 1.txt` and the calibration file.
3. **Inputs.** Do both conversions and report them separately:
   - (a) `int16 / 32768 × 2√2` Pa;
   - (b) as in the official `ISO_532-1_main.c`, a factor from the whole-file mean square of the Annex C calibration file at 60 dB.
   The official CLI needs no calibration file for float WAVs; integer WAVs need one. Record the hash of every input file.
4. **Implementations and variants** (each with "its own value" and "only this cell changed"; the variants must be reproducible and their diffs delivered):
   - Official C: build the CLI yourself from the sources with MSVC x64 `/O2 /fp:precise`. Unmodified = 0.22f; the variant changes only `USL[12][4]` to 0.24f (expected SHA-256 after substitution `739af24dee118027cb419fcdb051d8b56b274211d986140d66d7ff4b9d52a7e9`).
   - SQAT v2.0: GitHub `ggrecow/SQAT` tag `v2.0` (expected to resolve to `94f489c053d1366da05d5e62838c3f54ac7715c3`), `Loudness_ISO532_1`. Own value = 0.24; the variant changes `USL(13,5)` to 0.22. Run with MATLAB or GNU Octave and record the version and dependencies. **If neither can run it, mark this item BLOCKED with the reason; do not rewrite or port SQAT.**
   - MoSQITo 1.2.1: a pinned version (record the package or source hash). Own value = 0.24; the variant changes only that cell of `usl` in `_calc_slopes` to 0.22. Do not modify the installed files; use an isolated copy or a run-time substitution.
   - `iso532` 0.4.0: own value = 0.24; the variant changes only that cell in `iso532/src/tables.rs` to 0.22, built in an isolated copy.
   - Negative control: run at least one implementation with a clearly wrong value as well (for example 0.30) and confirm the method tells it apart.
5. **Reference and metrics** (the workbooks are the reference; time-varying signals at the workbook time points; stationary N from B8 and N′ from G8:G247):
   - Stationary signals 1–5: error of N, largest absolute error over the 240 N′ values. Signal 1 is a third-octave level input; use each implementation's corresponding entry point, or write "not applicable" if there is none.
   - Time-varying signals 6–25: largest and median absolute error and relative error of N(t); for signals 6–13 also N′(t) at the Bark value named in the workbook; Nmax; N5 over the row range of the workbook formula (note that the formulas of signals 12 and 13 reference column E).
   - Points outside `max(0.1, 0.05·|ref|)` (zero exceptions, no relaxation).
   - "Decisive points": points where the two official C builds differ by ≥ 2e-4 sone. At those points report each implementation's error for both variants, and how many points the workbook equals, or is closer to, each build.
   - Isolated effect of the cell: for each implementation, the largest absolute "own − variant" difference and the number of affected points.
   - Differences between implementations (for example SQAT against official C, MoSQITo against official C), to separate "this cell" from "other implementation differences".
6. **Output precision.** The official CLI prints four decimals, which limits resolution; state your criterion for "equal".
7. **Conclusions.** Answer each of the three questions of §1. Report any difference from the main agent's claim as a finding.

Out of scope: changing product code or goldens; buying the standard; deciding the normative Table A.9 value (this round measures only how implementations relate to the reference data).

## 3. Evidence rules

- Every number is produced by a script in the delivery folder and is reproducible from the frozen commit, the recorded toolchain and the input hashes. Deliver the harness sources (`.c`, `.rs`, `.m` with a `.txt` suffix).
- Do not include full third-party sources (SQAT is GPL-3.0, MoSQITo, ISO material); record versions, hashes and cited line numbers only. One-cell diffs may be delivered.
- Report each item as PASS / FAIL / BLOCKED / SKIPPED / PARTIAL; keep gaps as gaps.

## 4. Delivery

- Folder: `docs/verification/<YYYY-MM-DD>-F03-implementation-errors-493fd59/`, dated with the delivery day (Asia/Taipei); never overwrite an earlier folder.
- Files: `report.md` (Traditional Chinese) and `report.en.md` with the same structure and numbers; `results.json` (metrics per implementation × variant × signal, decisive-point counts, hashes); harness sources and run scripts; `delivery-check.md`; `delivery-integrity.json`, produced after redaction and explicitly excluding itself.
- Before delivery: run `python tools/redact_paths.py <folder>`, then `--check`; record their output (including skipped files and warnings) in `delivery-check.md`. Check suffixes the tool does not cover and non-UTF-8 files one by one; remove `__pycache__`. Only UTF-8 text files go into the folder; WAVs, executables and large CSVs are not committed, only hashed. Hashes of original inputs, binaries and tested sources keep their original meaning; do not claim that redacted copies are byte-identical to the originals.
- Use LF line endings; if any file has CRLF, state in `delivery-check.md` how it was handled and make sure `delivery-integrity.json` matches the bytes that will be committed.
- The delivery includes no commit or push. The main agent stages the folder, re-runs the redaction check and commits.
