# Delivery check

Own delivery of the main agent (Claude Opus 5.5), same rules as the auditor's deliveries.

- Redaction: `python tools/redact_paths.py <folder>` replaced 4 paths in `criterion/run_criterion.sh`; the Git Bash spelling of the repository path (`/<drive letter>/<repository>`) was not covered by the tool before this round, so `tools/redact_paths.py` gained rules for that spelling and the panel checkouts (the same rule also redacted 12 `cd` lines of that spelling in four July phase plans). `python tools/redact_paths.py --check docs` then prints `clean`. No skipped files or warnings were printed.
- Manual search of the folder for user names, user-profile paths, `AppData` and repository paths in any spelling found nothing after redaction.
- Formats: only `.md`, `.json`, `.log`, `.py`, `.sh`, `.txt` (all handled by the tool); every file decodes as UTF-8 and contains no NUL byte. The Rust harness is delivered as `.txt`. No binary, WAV, wheel, DLL, workbook or Criterion data directory is included.
- Line endings: 8 files written by Python on Windows had CRLF and were converted to LF before the manifest was computed: `binding-ab.log`, `compare-mosqito-v0.4.0.log`, `compliance-v0.3.1.json`, `compliance-v0.4.0.json`, `compliance.py`, `criterion/criterion-summary.json`, `criterion/summarize_criterion.py`, `pytest-wheel-v0.4.0.log`. Content is otherwise unchanged. All delivered files are LF, so no `.gitattributes` rule is needed.
- `delivery-integrity.json` lists the SHA-256 of every other file in the folder after redaction and line-ending conversion. Hashes of inputs, wheels and artifacts quoted in the reports and `environment.json` keep their original meaning (the original files in `tmp/`).
