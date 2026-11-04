# Replay and evidence map

Run from the repository root. Do not use moving main. `prepare.py` extracts candidate `fca4ccda18a8fbada77031425e5e683f1acd5a8d`, Round 1 `2fc1708`, and baseline `v0.3.1` with Python tarfile, preserving Unicode filenames. It refuses to overwrite existing snapshots. `source-integrity.json` records every tracked file against git archive; generated ignored data/build output are separate.

Prerequisites: recorded Rust/MSVC toolchain, Python with NumPy/openpyxl, original ISO archive under `tmp/c01-material/official`, official C/header under `tmp/c01-tail-root-cause-aa379db-run2/c`, and original MoSQITo fixtures under `data/golden` and `data/annexb`. Input hashes are delivered. These licensed/binary inputs are not redistributed here. `ISO532_VCVARS` overrides the default BuildTools vcvars path in the numerical runner. No report placeholder should be copied into an executable command; `<REPO>` and `<USER_HOME>` in logs are redacted provenance only. Scripts derive repository roots from cwd or their own location, or accept a repository-root argument.

Sequence:

1. `python <delivery>/prepare.py`; copy `data/golden` and `data/annexb` into the candidate's `data/` (the gate runner does this, preserving hashes).
2. `python <delivery>/generate-golden.py` using the NumPy interpreter. It runs the frozen generator, compares all manifest entries, restores the tracked manifest bytes that the generator rewrites, and exercises the bad-source negative control. Create the empty `tmp/acceptance-040-astra/golden-ready` marker after success for the gate runner. Optional existing `data/golden-c/meta.json` is only compared if its hash equals the frozen manifest entry.
3. `python <delivery>/gates/run_gates.py`; the separate `run_python.py`, `recover_python.ps1`, and `run_python_tests.py` document environment recovery; use the pinned complete pip-freeze. Set `PIP_NO_INDEX=0` if a shell inherited offline pip policy and install the recorded matplotlib dependency before pytest. `gates/run_linux.ps1` documents the isolated Linux container run.
4. `python <delivery>/run-numerics.py`; `python <delivery>/classify-f07.py`; `python <delivery>/diagnostic-controls.py`; `python <delivery>/supplemental-release-numbers.py`; `python <delivery>/compare-release.py`.
5. `python <delivery>/contracts/run_contracts.py .`; `python <delivery>/contracts/audit_sig15.py .`; `python <delivery>/audit-freeze.py`.
6. `python <delivery>/gates/summarize.py`; `python <delivery>/make-reports.py`; final redaction and delivery inventory as documented in `delivery-check.md`.

The C and Rust `.txt` files are actual harness sources; runners copy them into ignored build directories with compiler extensions. `classification-{old,new}.rs.txt` are explicitly source-derived tracing copies, used only to localize changes; they are not an independent mathematical oracle. The C wrapper and external Rust CLI supply independent end-to-end comparisons. Diagnostic C variants are not correctness references. Numerical arrays, DLLs, wheels, original C, WAVs and workbooks remain under ignored local paths; JSON hashes refer to their original bytes, not to redacted report text.

Tests are executed on isolated snapshots. No product code, test, golden fixture or decision file is edited. No stage/commit/push/tag/GitHub Actions run is part of this delivery. The frozen generator's temporary manifest rewrite was restored byte-for-byte and the final source audit checks this.
