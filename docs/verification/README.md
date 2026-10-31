# Independent verification deliveries

Each verification round gets its own folder named `<date>-<topic>-<tested commit>`
with a self-contained report (scope, versions, method, results, limits, evidence
locations). A new round never appends to an earlier report; it links to it. Checks
that were not re-run are marked as historical evidence.

## Evidence archives

Full evidence packages (frozen source archive, official ISO material, C builds,
run directories, per-case outputs) are too large for Git. They are distributed as
ZIP files from a shared cloud drive; only the report, the JSON/CSV summaries, the
logs and the runner script are tracked here. Verify a download against the SHA-256
below before unpacking it into a new, empty directory.

| round | tested commit | archive | size | SHA-256 | download |
|---|---|---|---|---|---|
| 2026-10-31 audit (pre-fix), `docs/修正報告.md` §10 | `aea3f37` baseline | `ISO532-verification-evidence.zip` | 1.9 MB | `dec6fcfd08be7a284c1e86604348c919151a87e82c6af8bc3f4cd3ea2f0be51a` | link pending |
| 2026-10-31 audit, Annex B deep analysis, `docs/修正報告.md` §11 | same | `AnnexB深入分析證據.zip` | 7.7 MB | `2014a3a7644dbe7b11594d0451dbd380ef6a28aded19867d7f773e77afbef232` | link pending |
| 2026-10-31 post-F-01 verification, `docs/修正後獨立驗證報告.md` | `3dc420c`, `6aea8b3` | `修正後獨立驗證證據-6aea8b3.zip` | 282 MB | `9872f0e6b6e176684a8e1f80494a90159e088e27e963a51fb7cf37fdc46ea104` | link pending |
| 2026-10-31 F-02 verification, [`2026-10-31-F02-5450d39/`](2026-10-31-F02-5450d39/) | `5450d39` | `F02獨立驗證證據-5450d39.zip` | 335 MB | `9f777b6c9f717a57f6045a1a0c5f37d9ec65c7073d099fd8f9af9ae2c392add0` | link pending |

Fill the download column with the cloud-drive link once the archive is uploaded.
A link alone is not evidence; the hash is what ties the download to the report.

Check a download on Windows:

```powershell
certutil -hashfile .\F02獨立驗證證據-5450d39.zip SHA256
```

or on Linux / macOS / Git Bash:

```bash
sha256sum F02獨立驗證證據-5450d39.zip
```

## Redaction of workstation paths

Reports and logs produced outside the repository quote absolute paths from the
auditor's machine. Before they are committed they are passed through
`tools/redact_paths.py`, which replaces the identifying prefixes with fixed
placeholders:

| placeholder | meaning |
|---|---|
| `<AUDIT_PYTHON>` | interpreter bundled with the auditor's tooling |
| `<AUDIT_HOME>` | the auditor's working-directory root |
| `<USER_HOME>` | any other path under the auditor's user profile |
| `<REPO>` | this repository's working copy |
| `<PANEL_REPO>` | the `iso532-rs-panel` working copy |

Redaction changes the bytes of the tracked copies. The SHA-256 values recorded in a
round's delivery manifest (`交付完整性.json`) therefore carry two fields: `sha256`
is the hash of the original file as preserved inside the evidence archive, and
`sha256_redacted` is the hash of the tracked copy after redaction. The archives
themselves are not modified.

`python tools/redact_paths.py --check docs` must print `clean` before a release.
