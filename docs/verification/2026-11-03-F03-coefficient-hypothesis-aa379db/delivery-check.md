# Delivery audit / 交付檢查

Date: 2026-11-03 (Asia/Taipei). Tested source snapshot: `aa379db8f3dc37f5048ac6c8b7a6d4ba2a6c3b76`. Final experiment run: `tmp/f03-coefficient-hypothesis-aa379db-run3`; prior runs remain separately in tmp and are not overwritten.

## Execution and evidence boundary

- All scoped harness assertions passed. The final run includes 48 arithmetic results, exact Fraction/Decimal 80/120 checks, positive/negative layout tests, boundary diagnostics, C/Rust target traces and actual isolated MoSQITo stage tests.
- `run-log.json` records subprocess commands, return codes and captured output. In-process Python/NumPy assertions and stages are represented by the harness and `results.json`; the log is not claimed to be a transcript of every operation.
- MSVC setup emitted a `vswhere.exe` PATH warning. x64 initialization, compilation and executable runs succeeded. This warning remains in the log and bilingual reports. A later read-only `cl /Bv` probe records MSVC 19.44.35228 x64; because it supplies no source, D8003/exit 2 is expected and is identified as a version probe, not a compilation gate failure.
- Original source and binary hashes in `results.json` refer to original inputs and tmp artifacts. Derived-source hashes refer to generated tmp source bytes. Delivery hashes refer to the delivered bytes after redaction and LF normalization. The redacted log and normalized diffs are not claimed bit-identical to the originals.
- Production files, goldens and previous verification rounds remain unchanged. Only this new delivery folder is added. No staging, commit, push or tag was performed. Full product/Annex B acceptance, historical intent and authorized normative-cell evidence remain outside the passed scope.

## Redaction and text format

Executed `python tools/redact_paths.py <delivery-folder>`, then `python tools/redact_paths.py --check <delivery-folder>`: first pass replaced 15 path occurrences in `run-log.json`; check returned `clean`.

The directory mode recognizes `.md`, `.json` and `.py` here, but does **not** include `.c` or `.diff`. Therefore `numeric.c` and all five diff files were explicitly passed as individual files to both normal and `--check` modes. They required zero replacements and checked `clean`. No non-UTF-8 skipped warnings occurred. All files are independently decoded as UTF-8 and inspected; there are no binaries or unexamined suffixes in this delivery.

Every file is normalized to LF and exactly one terminal newline, then redaction checks are repeated across the full explicit file list. The final integrity manifest is generated last and excludes only itself. Manifest verification confirms exact file-set equality, byte lengths and SHA-256 hashes. A manifest can be regenerated after any reviewer edits; an earlier hash must not be reused for edited bytes.

## Review

Reviewed the new-file diff, bilingual report numbers, source positions, generated instrumentation diffs and finite/negative-control outcomes. C instrumentation only adds a target-read counter. Rust instrumentation adds a counter at the existing lookup; its 0.22 table variant changes one cell. Python diffs remove a package import for isolated helper injection and change only the target literal in the 0.22 variant. The helper remains unchanged apart from copy newline normalization.

No official full text, preserved implementation source tree, PDF, executable, object file or debug symbols is redistributed. `sources.md` identifies public URLs and explicit primary-source/authority limits. Missing authorized Table A.9 remains PENDING even though numerical gates passed.
