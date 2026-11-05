# Delivery check

Own delivery of the main agent (Claude Opus 5.5), same rules as the auditor's deliveries.

- Redaction: `python tools/redact_paths.py <folder>` replaced 1 path (the `iso532` path dependency in `zwst_frontend_harness.Cargo.toml.txt`); `--check` on the folder and on `docs` then prints `clean`; no skipped files or warnings. A manual search for user names, user-profile paths, `AppData` and repository paths in any spelling found nothing.
- Formats: `.json`, `.md`, `.py`, `.txt` only, all handled by the tool. The Rust harness, its manifest and the JSON-lines outputs are delivered as `.txt`. Every file decodes as UTF-8 without NUL bytes. Problems: none.
- Line endings: 1 files written on Windows had CRLF and were converted to LF before the manifest was computed: `filter-response.json`.
- Not delivered: the harness build, the Annex B inputs (hashes in the 2026-11-04 Astra round) and the MoSQITo source archive.
- `delivery-integrity.json` lists the SHA-256 of every other file after redaction and line-ending conversion.
