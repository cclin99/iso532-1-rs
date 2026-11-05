# Delivery check

Own delivery of the main agent (Claude Opus 5.5), same rules as the auditor's deliveries.

- Redaction: `python tools/redact_paths.py <folder>` changed 0 files; `--check` on the folder and on `docs` prints `clean`; no skipped files or warnings. A manual search for user names, user-profile paths, `AppData` and repository paths in any spelling found nothing. The standard MSVC install path in the two build commands is kept, as in earlier deliveries.
- Formats: `.json`, `.md`, `.py`, `.txt` only, all handled by the tool; the build commands are delivered as `.txt`. Every file decodes as UTF-8 without NUL bytes. Problems: none.
- Line endings: 6 files had CRLF and were converted to LF before the manifest was computed: `build-v022.cmd.txt`, `build-v024.cmd.txt`, `compare.json`, `decisive-points.json`, `float-wavs.json`, `two-cli-compare.json`.
- Not delivered: float WAVs, the two CLI executables, their `Loudness.csv` / `SpecLoudness.csv` outputs, the official sources, workbooks and the SQAT source (GPL-3.0); their SHA-256 are in `sources-and-hashes.json` and `float-wavs.json`. Only line 519 of the SQAT file is quoted.
- `delivery-integrity.json` lists the SHA-256 of every other file after redaction and line-ending conversion.
