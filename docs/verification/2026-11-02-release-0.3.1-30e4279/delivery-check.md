# Delivery audit

- Line endings: all delivered text is normalized to LF before redaction/hashing; original source/input/binary hashes retain their raw-object meaning.
- Status: PASS. All delivered files decode as UTF-8; no binary/WAV/wheel payloads are included.
- Required directory redaction followed by --check completed. Unknown suffixes were passed explicitly as individual files and checked again.
- No non-UTF8 skipped files or tool warnings. Directory mode silently omits unknown suffixes; the explicit-file pass closes this gap.
- Post-redaction integrity covers all delivery files except delivery-integrity.json itself. Original source/input/binary hashes retain their raw-object meaning.

## Redactor output

```text
0 file(s) changed
0 file(s) changed
clean
clean
```

## Complete text inventory

Files (excluding integrity manifest): 116. Suffix counts: {".c": 1, ".cmd": 1, ".json": 14, ".jsonl": 2, ".lock": 3, ".log": 70, ".md": 6, ".ps1": 1, ".py": 15, ".rs": 2, ".toml": 1}. Non-UTF8: 0. NUL-containing files: 0. Residual identifying paths: 0.

| File | UTF-8 | Directory mode |
|---|---|---|
| archive-extraction.json | yes | covered |
| artifact-runtime.json | yes | covered |
| artifacts.json | yes | covered |
| audit_artifacts.py | yes | covered |
| audit_metadata.py | yes | covered |
| baseline-ffi-build.log | yes | covered |
| ci.json | yes | covered |
| clippy.log | yes | covered |
| clippy_all.log | yes | covered |
| compiler.log | yes | covered |
| contracts/c-build.log | yes | covered |
| contracts/c-client.c | yes | explicit file pass |
| contracts/c-results.jsonl | yes | explicit file pass |
| contracts/ffi-build.log | yes | covered |
| contracts/prepare-sig3.py | yes | covered |
| contracts/python-client.py | yes | covered |
| contracts/python-results.json | yes | covered |
| contracts/README.md | yes | covered |
| contracts/results.json | yes | covered |
| contracts/run-c.cmd | yes | explicit file pass |
| contracts/run.ps1 | yes | covered |
| contracts/rust/Cargo.lock | yes | explicit file pass |
| contracts/rust/Cargo.toml | yes | covered |
| contracts/rust/src/main.rs | yes | explicit file pass |
| contracts/rust-build.log | yes | covered |
| contracts/rust-results.jsonl | yes | explicit file pass |
| contracts/sig3-input.json | yes | covered |
| contracts/summarize.py | yes | covered |
| delivery-check.md | yes | covered |
| doc_pairs-retry.log | yes | covered |
| doc_pairs.log | yes | covered |
| ffi_release.log | yes | covered |
| finalize.py | yes | covered |
| fmt.log | yes | covered |
| formal-gates.json | yes | covered |
| freeze.json | yes | covered |
| gate_evidence.py | yes | covered |
| gates.json | yes | covered |
| golden.log | yes | covered |
| hash-gate-strict.log | yes | covered |
| maturin-retry.log | yes | covered |
| maturin.log | yes | covered |
| numerics/augment.py | yes | covered |
| numerics/bin-1.log | yes | covered |
| numerics/bin-15.log | yes | covered |
| numerics/bin-17.log | yes | covered |
| numerics/bin-7.log | yes | covered |
| numerics/bin-9.log | yes | covered |
| numerics/blank-csv.log | yes | covered |
| numerics/bom-csv.log | yes | covered |
| numerics/empty-bin.log | yes | covered |
| numerics/empty-csv.log | yes | covered |
| numerics/harness.rs | yes | explicit file pass |
| numerics/hash-gate.log | yes | covered |
| numerics/header_only-csv.log | yes | covered |
| numerics/margin-10.log | yes | covered |
| numerics/margin-3.log | yes | covered |
| numerics/margin-5.log | yes | covered |
| numerics/missing_row-csv.log | yes | covered |
| numerics/nan-bin.log | yes | covered |
| numerics/nan-csv.log | yes | covered |
| numerics/negative-bin.log | yes | covered |
| numerics/neginf-bin.log | yes | covered |
| numerics/neginf-csv.log | yes | covered |
| numerics/new-build.log | yes | covered |
| numerics/new-Cargo.lock | yes | explicit file pass |
| numerics/new-input-0.log | yes | covered |
| numerics/new-input-1.log | yes | covered |
| numerics/new-input-2.log | yes | covered |
| numerics/new-input-3.log | yes | covered |
| numerics/new-input-4.log | yes | covered |
| numerics/new-input-5.log | yes | covered |
| numerics/new-input-6.log | yes | covered |
| numerics/new-input-7.log | yes | covered |
| numerics/old-build.log | yes | covered |
| numerics/old-Cargo.lock | yes | explicit file pass |
| numerics/old-input-0.log | yes | covered |
| numerics/old-input-1.log | yes | covered |
| numerics/old-input-2.log | yes | covered |
| numerics/old-input-3.log | yes | covered |
| numerics/old-input-4.log | yes | covered |
| numerics/old-input-5.log | yes | covered |
| numerics/old-input-6.log | yes | covered |
| numerics/old-input-7.log | yes | covered |
| numerics/posinf-bin.log | yes | covered |
| numerics/posinf-csv.log | yes | covered |
| numerics/README.md | yes | covered |
| numerics/results.json | yes | covered |
| numerics/run.py | yes | covered |
| numerics/unparsable-csv.log | yes | covered |
| numerics/validator-controls.log | yes | covered |
| numerics/verdict-10-tv_n.log | yes | covered |
| numerics/verdict-3-st_n.log | yes | covered |
| numerics/verdict-3-st_spec.log | yes | covered |
| numerics/verdict-5-st_n.log | yes | covered |
| numerics/verdict-5-st_spec.log | yes | covered |
| old-exports.log | yes | covered |
| prepare.py | yes | covered |
| pytest-formal.log | yes | covered |
| pytest.log | yes | covered |
| README.md | yes | covered |
| record_observed_run.py | yes | covered |
| records.json | yes | covered |
| redact_docs-retry.log | yes | covered |
| redact_docs.log | yes | covered |
| release-exports.log | yes | covered |
| report.en.md | yes | covered |
| report.md | yes | covered |
| results.json | yes | covered |
| run_gates.py | yes | covered |
| rust_tests.log | yes | covered |
| summarize.py | yes | covered |
| summary-negative-controls.json | yes | covered |
| test_summary_controls.py | yes | covered |
| wheel-install-probe.log | yes | covered |
| wheel_probe.py | yes | covered |
