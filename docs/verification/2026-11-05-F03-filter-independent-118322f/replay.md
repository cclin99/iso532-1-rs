# Replaying this independent verification

Numerical execution and bilingual findings were produced by Astra (`gpt-6-astra`). The coordinating agent reviewed the claims against the delivered numerical files and completed delivery packaging. This is an experiment harness, not a proposed product implementation.

## Inputs and environment

Use a separate checkout containing commit `118322f8300dc752f1d38a79db230a2db5ff2870`; the orchestration checkout was `493fd595ef62aaded72ed57af1a75327ba14a5b0`. Run commands from its repository root. Do not rerun in this original delivery directory: the scripts write numerical outputs beside themselves and use the fixed local experiment directory `tmp/verification-f03-filter-independent/`.

Copy the legally available preserved raw-material tree to `tmp/c01-material/official/` in that separate checkout, preserving the relative names in [frozen-inputs.json](frozen-inputs.json). It contains the original WAVs, XLSX workbooks, and C/header files. These source materials and large generated outputs are not redistributed in this delivery. Missing sources block a complete replay; previously computed JSON is not a substitute.

Create a new dated verification directory in the separate checkout. Copy `preregistration.md`, `freeze.py`, `replay.py`, `frontend.rs.txt`, `frontend.Cargo.lock.txt`, `analyze.py`, `rounding_audit.py`, and optionally `make_reports.py` there. Keep the original delivered manifest separately for hash comparison; do not copy it as the new round's `frozen-inputs.json`, because `freeze.py` deliberately creates that file exclusively.

The recorded environment is in [tools.json](tools.json): Python 3.11.9, NumPy 2.4.4, openpyxl 3.1.5, Rust 1.99.1 and Cargo 1.99.1, Windows x64 MSVC. Select the matching Python environment before running the commands. `replay.py` expects the MSVC 2022 BuildTools `vcvars64.bat` system installation shown in the build command files, and cached Cargo dependencies (`--offline`). If the toolchain installation differs, record the adaptation in the new round. Binary hashes can vary with toolchain/build metadata and are provenance, not unconditional cross-machine bitwise gates.

## Command order

In PowerShell, replace the following relative destination with the new round's directory:

```powershell
$round = 'docs/verification/<new-date>-F03-filter-independent-replay-118322f'
python "$round/freeze.py"
New-Item -ItemType Directory -Force tmp/verification-f03-filter-independent/rust | Out-Null
Copy-Item -LiteralPath "$round/frontend.Cargo.lock.txt" -Destination tmp/verification-f03-filter-independent/rust/Cargo.lock
python "$round/replay.py"
python "$round/analyze.py"
python "$round/rounding_audit.py"
```

Check each command's exit status before continuing. Compare the new frozen raw-input/product hashes with this round before accepting results. `freeze.py` extracts exact tag bytes with `git show`; the harness does not compile the current product working tree. The isolated harness includes `[workspace]`, preserving the fix for the first build's workspace-membership failure. That first failure is retained as an environment failure, not a numerical test failure.

`replay.py` rebuilds both official C variants and the independent Rust harness, writes new Pa inputs, runs all 48 CLI cases, reads the workbooks afresh, and records hashes. `analyze.py` uses fresh DLL calls for full-precision and matched-skip controls and produces the factorial/summary files. `rounding_audit.py` reconstructs the old floating-distance count and the corrected decimal-integer count from the new CSVs. `make_reports.py` contains this round's prose template and some fixed observations; it is not a general verdict generator. A replay must review its own numerical results and write new conclusions rather than blindly reusing that prose.

## Evidence map and interpretation

- `workbook-comparison.json`, `alignment.json`, `summary.json`: exact time matching, N/N′ counts, first failures, maximum-error coordinates, and decimal threshold sensitivity. `exploratory_shared_threshold_exceptions_*` is an exploratory shared threshold, not a complete Annex B compliance assessment.
- `factorial.json`, `frontend-results.jsonl.txt`: four stationary inputs, two calibrations, both frontends, skip sensitivity, and band levels. `frontend_method_delta_sone` includes the change of RMS interval; `matched_skip_filter_effects` controls that interval.
- `c-fullprecision-controls.json`, `skip-and-band-sensitivity.json`, `float-precision-controls.json`, `bypass-negative-controls.json`, `negative-time-shift.json`, `length-boundaries.json`: source of the causal controls and limitations.
- `rounding-audit.json`: all 47 mathematically tied points that the old binary-float predicate classified differently.
- `frozen-inputs.json`, `builds.json`, `generated-input-hashes.json`, `raw-output-hashes.json`, `tools.json`: original input, tested source, generated input/output, and executable provenance. They are distinct from delivery-copy integrity hashes.

Finish the new round with both path-redaction passes, unsupported-format/non-UTF-8 inspection, and a new integrity manifest. Preserve this round unchanged. Numerical agreement cannot close the corrected Table A.9 authority gate.
