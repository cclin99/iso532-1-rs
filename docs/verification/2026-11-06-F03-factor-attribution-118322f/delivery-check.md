# Delivery check

Own delivery of the main agent (Claude Fable 5.1), same rules as the auditor's deliveries.

- Redaction: first pass output and `--check` are in `redaction.log`; final `--check` after the log was written: `clean`.
- Manual search (case-insensitive) for the user name, user-profile folders and repository paths in any spelling: nothing found.
- Formats: `.md`, `.json`, `.py`, `.txt`, `.log` only (Rust, MATLAB/Octave and diff sources delivered as `.txt`), all covered by the tool. UTF-8 / NUL problems: none.
- Line endings: 11 files had CRLF and were converted to LF before the manifest was computed: `analyze.log`, `calibration.json`, `delivery-check.md`, `delivery-integrity.json`, `report.en.md`, `report.md`, `results.json`, `run-factorial.log`, `sqat-eps0-022.diff.txt`, `sqat-eps0-024.diff.txt`, `validate.log`.
- Not delivered: stage dumps, factorial cell outputs, Octave outputs, the official CLI outputs, WAV-derived inputs, the official sources and workbooks, the SQAT source (GPL-3.0; only the one-line diffs are delivered). Their SHA-256 are in `raw-output-hashes.json` (unredacted binaries; these hashes keep their original meaning).
- `delivery-integrity.json` lists the SHA-256 of every other file after redaction and line-ending conversion, excluding itself.
