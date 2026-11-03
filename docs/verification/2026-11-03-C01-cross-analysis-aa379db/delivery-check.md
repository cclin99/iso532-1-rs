# Delivery check / 交付檢查

Claude's own cross-analysis delivery, filed under the same rules as Astra deliveries (AGENTS.md). No production source, test, golden or prior evidence folder was changed. The two index files (`docs/verification/README.md`, `docs/README.md`) and the decision memo / phase plan are outside this folder and are committed together with it.

本資料夾是 Claude 自己的交叉分析，依與 Astra 交付相同的規則進庫；未改任何程式、測試、golden 或既有證據資料夾。

## Provenance / 來源

- All scripts were first written in the session scratchpad with hard-coded scratch paths, then parametrized (`C01_WORK`, `C01_E2E_OUT`, `__file__`) and re-run from this folder on 2026-11-03 to produce `logs/`. The numbers in the reports are from these re-runs.
- `band0_real.log` was produced by the scratch cargo project; its `main.rs` carries one extra duplicate case line relative to `band0_real-main.rs.txt` (noted in the report §3.6).
- External inputs (official C, Astra's wrapper DLL and probe executable, Astra's stage arrays) stay in `tmp/`; their SHA-256 values are in `inputs.sha256.txt` and keep their original meaning (unredacted bytes).

## Redaction and coverage / 去識別化與範圍

- `python tools/redact_paths.py docs/verification/2026-11-03-C01-cross-analysis-aa379db`: 1 file changed (`band0_real-Cargo.toml.txt`, repo path → `<REPO>`); no skipped-file warning on stderr.
- `python tools/redact_paths.py --check …`: `clean`, exit 0.
- File suffixes present: `.md`, `.py`, `.log`, `.txt`, `.json` (manifest). All are in the tool's `TEXT_SUFFIXES`; no uncovered format.
- Every file strictly decodes as UTF-8. A `__pycache__/` directory created by the re-run contained absolute paths and was deleted before the manifest was generated; it is also in the tool's `SKIP_DIRS` and must never be delivered.
- Manual grep over the folder for user name, `C:\Users`, `AppData`, drive-letter repo paths, session id, machine name and backslash paths: no residual identifiers after the cache deletion.
- The scripts read paths only from environment variables; no absolute path is embedded.

## Hash meaning / Hash 語意

`delivery-integrity.json` lists the final post-redaction UTF-8 bytes of every file in this folder except itself (git `core.autocrlf=true`: the hashes correspond to the LF bytes stored in git; a Windows checkout yields CRLF, as for all earlier rounds). `inputs.sha256.txt` hashes the external inputs as they are, not redacted copies.
