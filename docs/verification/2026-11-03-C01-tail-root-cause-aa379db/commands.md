# Reproduction and execution record

All numerical calculations were performed this round. Frozen pressure inputs and old expected baseline bits are explicitly reused from the preceding C-01 round; outputs are recomputed. Preserve all previous folders. This round's successful scratch is `tmp/c01-tail-root-cause-aa379db-run2`; failed wrapper attempt is `tmp/c01-tail-root-cause-aa379db-run1`.

## Actual successful primary run

```powershell
python docs/verification/2026-11-03-C01-tail-root-cause-aa379db/run_experiment.py --work tmp/c01-tail-root-cause-aa379db-run2 --prior-work tmp/c01-zero-pad-aa379db-run1 --prior-results docs/verification/2026-11-03-C01-zero-pad-aa379db/results.json --official tmp/c01-material/official --archive tmp/c01-material/iso532-official.zip --vcvars "C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Auxiliary/Build/vcvars64.bat"
```

Exit 0. `run-log.json` records exact archive/build/probe commands, compiler versions, stdout/stderr and exit codes. The C wrapper includes the byte-identical official C compilation unit; separate Rust modules are generated from the fixed source, with every transformation delivered as diff. All source hashes remain pinned. Internal C return values and input immutability are assertion gates in the delivered runner; final bitwise public/replay equivalence is recorded per signal.

The earlier Python syntax error and first C wrapper mutation failure are preserved in preflight-errors.log and attempt-1-*; wrapper-correction.diff.txt records the copy-before-call repair. The full run was repeated after repair. There was no tolerance/source-algorithm change. `cl /Bv` with no source returns 2/D8003 as an expected version query; MSVC environment emits a nonfatal vswhere lookup warning. Neither is a numerical failure hidden as a pass.

## Bounded exploratory controls, in execution order

```powershell
python docs/verification/2026-11-03-C01-tail-root-cause-aa379db/main_literal_controls.py --work tmp/c01-tail-root-cause-aa379db-run2 --vcvars "C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Auxiliary/Build/vcvars64.bat"
python docs/verification/2026-11-03-C01-tail-root-cause-aa379db/slopes_controls.py --work tmp/c01-tail-root-cause-aa379db-run2 --vcvars "C:/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Auxiliary/Build/vcvars64.bat"
python docs/verification/2026-11-03-C01-tail-root-cause-aa379db/r8_control.py --work tmp/c01-tail-root-cause-aa379db-run2
```

All exited 0. Each has its own dated pre-execution addendum, log, variants/diffs and before/after source/binary hashes. These scripts append explicit exploratory sections to results.json; primary-results.json preserves the primary-only result. The r8 control reuses the first probe's Cargo target cache under a distinct executable name and verifies the original probe binary hash is unchanged. It does not mutate the original snapshot or executable. These variants are diagnostic interventions, not repairs or alternative authoritative references.

## Fresh reproduction

The scripts use their own directory as the delivery destination and reject an existing results.json/new scratch collision. Copy the design, runner, native templates and supplemental scripts to a NEW delivery directory before invoking them; do not rerun inside this completed folder. Use a NEW scratch. Supply the same official archive/extracted tree, original calibrated pressure bytes and prior baseline JSON; their hashes are recorded. If raw pressure files are unavailable, regenerate them using the preceding C-01 round's delivered decoder/runner and require matching input hashes before proceeding.

Run the primary script first, then the three supplements in the order above. Build flags are MSVC /nologo /O2 /fp:precise; Rust release/offline with an isolated manifest/lock. The primary runner pins commit aa379db8f3dc37f5048ac6c8b7a6d4ba2a6c3b76 via git archive rather than following HEAD. Full arrays remain in scratch as little-endian binary64; multiband stages are row-major [band,time]. Source-input-hashes.json and per-control JSON list raw identity, while delivery-integrity.json lists final post-redaction text identity.

## Evidence map

- results.json: final primary plus exploratory controls; primary-results.json: primary-only snapshot.
- tail-decomposition.csv: all 28 ordered target values, bits, signed contributions and fractions.
- stage-coordinates.csv: chronological first differences, maxima and target-worst values with decimal17/binary64 bits.
- exploratory-tails.csv: all 32 exploratory target values and bits.
- run-start.json and experiment-design*.md: unchanged preregistration hashes; exploratory/slopes/r8 addenda explicitly distinguish post-primary hypotheses.
- stages.c.txt and probe.rs.txt: baseline replay harness; every source adaptation has a complete *.diff.txt plus generator script.
- main-literal-controls.json / slopes-controls.json / r8-control.json: precise remaining differences and source/binary/raw-array hashes.
- delivery-check.md / delivery-integrity.json: final path-redaction/UTF-8/diff review and integrity, completed by the main agent after numerical-author handoff.

No full workspace/package/binding/performance suite was rerun. No production DSP, tests, goldens, decisions, audit closure row, prior evidence, commit or push was changed.
