# Delivery check

Own delivery of the main agent (Claude Opus 5.5), same rules as the auditor's deliveries.

- Redaction: first pass output and `--check` are in `redaction.log`; final `--check` after the log was written: `clean`.
- Manual search (case-insensitive) for the user name, user-profile folders and repository paths in any spelling: nothing found.
- Formats: `.md`, `.json`, `.py`, `.txt`, `.log` only (Rust sources and Cargo files delivered as `.txt`), all covered by the tool. UTF-8 / NUL problems: none.
- Line endings: 4 files had CRLF and were converted to LF before the manifest was computed: astra_residual.json, run-astra_residual.log, run-crosscheck.log, run-usl_main_effect_definition.log.
- Not delivered: the harness build, the Claude factor-attribution cell outputs (hashes in that round's `raw-output-hashes.json`), the workbooks. Astra's files are read in place from their tracked folders and are not copied.
- `delivery-integrity.json` lists the SHA-256 of every other file after redaction and line-ending conversion, excluding itself.
