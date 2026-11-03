# Commands and reproduction

Run date: 2026-11-03 (Asia/Taipei). Use a new scratch directory and a new output directory for every reproduction. Original material is required; do not substitute MoSQITo. The archived original C hash and all input hashes are in source-input-hashes.json.

The local material was extracted from `target/verification/2026-10-31-F02-5450d39/F02獨立驗證證據-5450d39.zip`, member `work/iso532-official.zip`, then expanded under `tmp/c01-material/official`. This was a source/material acquisition step, not reuse of prior numerical results. For reproduction, obtain the same official archive (hash in source-input-hashes.json) and extract it unchanged.

## Actual primary command

```powershell
python docs/verification/2026-11-03-C01-zero-pad-aa379db/run_experiment.py --official tmp/c01-material/official --archive tmp/c01-material/iso532-official.zip --vcvars "C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Auxiliary/Build/vcvars64.bat" --work tmp/c01-zero-pad-aa379db-run1
```

This command ran the original harness now preserved as attempt-1-run_experiment.py.txt. Top-level exit code: 0. Its stdout reported four WITHIN TOLERANCE verdicts, a failed strict-rounding gate and a confounded comparator control. All subprocesses and library returns are in run-log.json. No build/result is borrowed from another round.

## Same-round isolated control repair and diagnosis

```powershell
python docs/verification/2026-11-03-C01-zero-pad-aa379db/repair_control.py
python docs/verification/2026-11-03-C01-zero-pad-aa379db/diagnose_history.py --work tmp/c01-zero-pad-aa379db-run1 --out docs/verification/2026-11-03-C01-zero-pad-aa379db
python docs/verification/2026-11-03-C01-zero-pad-aa379db/render_reports.py
```

All exited 0. repair_control.py is a forensic record of the one-time correction; do not run it again on the corrected runner. It preserves original results/runner, changes only the control call site, extracts the unchanged compare function, reconstructs C reference values from binary64 bits and reruns that isolated control. No primary source/input/output arrays or threshold are altered. control-correction.diff.txt records the complete harness correction.

## Fresh reproduction with corrected harness

Create NEW_OUTPUT first; NEW_WORK must not exist. The delivered runner reads the paired design and wrapper/probe templates beside itself, then writes into the new output directory. Fill each angle-bracket placeholder with an explicit local path.

```text
python run_experiment.py --repo <REPO> --official <EXTRACTED_OFFICIAL_ARCHIVE> --archive <OFFICIAL_ZIP> --vcvars <VCVARS64_BAT> --work <NEW_WORK> --out <NEW_OUTPUT>
python diagnose_history.py --work <NEW_WORK> --out <NEW_OUTPUT>
```

The runner archives exactly commit aa379db8f3dc37f5048ac6c8b7a6d4ba2a6c3b76. It rebuilds the unchanged official C/CLI and the separate Rust probe, tests all primary/control/boundary cases, and runs the fixed-snapshot output_grid contract tests. The corrected call site means no separate repair is needed in a fresh reproduction. The first-attempt confounding is retained only as historical evidence of this same round.

C flags are /nologo /O2 /fp:precise (and CRT diagnostic suppression); exact build batch is build-c.cmd.txt. Native wrapper/probe templates use .txt to remain covered by the path-redaction scanner. The separate Rust probe manifest/lock are delivered. Versions, build output, execution output and exit codes are in run-log.json. `cl /Bv` exit 2 is an expected no-source version query, not a failed numerical computation.

## Delivery checks

```text
python tools/redact_paths.py docs/verification/2026-11-03-C01-zero-pad-aa379db
python tools/redact_paths.py --check docs/verification/2026-11-03-C01-zero-pad-aa379db
```

See delivery-check.md for the full UTF-8/extension inventory and final pass results. Once all delivered text is final, delivery-integrity.json hashes the post-redaction bytes and excludes itself. Raw source/input/binary/harness hashes remain labels for their original material and are not changed to impersonate final-delivery hashes.
