# Independent verification deliveries

Each verification round gets its own folder named `<date>-<topic>-<tested commit>`
with a self-contained report (scope, versions, method, results, limits, evidence
locations). A new round never appends to an earlier report; it links to it. Checks
that were not re-run are marked as historical evidence.

## Briefs to the auditor

Round briefs handed to the independent auditor live under `briefs/` as
`<date>-<topic>.md` with a Traditional-Chinese counterpart `<date>-<topic>.zh-TW.md`
(policy: `docs/DOCUMENTATION-LANGUAGE-POLICY.md`). Since 2026-10-31 every delivery
folder contains both `report.md` (Chinese) and `report.en.md` (English), written by
the auditor. Deliveries before that date are Chinese only; this index carries their
English summary.

| brief | issued | status |
|---|---|---|
| [`briefs/2026-11-01-F03-B-aarae-lineage.md`](briefs/2026-11-01-F03-B-aarae-lineage.md) | 2026-11-01 | open: lineage of the `USL[12][4]` value 0.24 through AARAE 2015 and the 2014 C program |
| [`briefs/2026-11-01-C01-zero-pad-reference.md`](briefs/2026-11-01-C01-zero-pad-reference.md) | 2026-11-01 | delivered 2026-11-03: [`2026-11-03-C01-zero-pad-aa379db/`](2026-11-03-C01-zero-pad-aa379db/) PARTIAL; four specific tails agree within 1e-14, but total tails only WITHIN TOLERANCE; prefix invariance, negative controls and eight boundaries pass; numerical gap remains open. Separate [tail root-cause experiment](2026-11-03-C01-tail-root-cause-aa379db/) quantifies rounding, slope and main-loudness contributions; it is not a production fix or closure |
| [`briefs/2026-11-01-release-0.3.1-acceptance.md`](briefs/2026-11-01-release-0.3.1-acceptance.md) | 2026-11-01 | delivered 2026-11-02: [`2026-11-02-release-0.3.1-30e4279/`](2026-11-02-release-0.3.1-30e4279/) ACCEPT, 8/8 items passed; tag `v0.3.1` released on it |
| [`briefs/2026-11-04-release-0.4.0-acceptance.md`](briefs/2026-11-04-release-0.4.0-acceptance.md) | 2026-11-04 | delivered 2026-11-04: [`2026-11-04-release-0.4.0-fca4ccd/`](2026-11-04-release-0.4.0-fca4ccd/) PARTIAL, 7/9 items passed; no numeric or API release blocker. §6 partial: the public stream frame carries no specific loudness, so stream-specific equality cannot be checked (existing capability gap, not a regression); §9 failed: the release commit table omitted `5bbbb93` (documentation finding, corrected in the release record) |

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
| 2026-10-31 F-03 sensitivity probe, [`2026-10-31-F03-sensitivity-d623d32/`](2026-10-31-F03-sensitivity-d623d32/) | `d623d32` | text-only delivery (report, scripts, `summary.json`, `run.log`); binary run outputs stay in the auditor's `tmp/`, not archived | – | – | n/a |
| 2026-10-31 F-03 authority trace, [`2026-10-31-F03-authority-d623d32/`](2026-10-31-F03-authority-d623d32/) | `d623d32` | text-only delivery (report, sources, acquisition checklist, literature follow-up) | – | – | n/a |
| 2026-10-31 F-03 SQAT source check, [`2026-10-31-F03-SQAT-d623d32/`](2026-10-31-F03-SQAT-d623d32/) | `d623d32` | text-only delivery (report, sources) | – | – | n/a |
| 2026-11-02 release 0.3.1 pre-tag acceptance, [`2026-11-02-release-0.3.1-30e4279/`](2026-11-02-release-0.3.1-30e4279/) | `30e4279` | text-only delivery (reports, harness sources, logs, `results.json`, `delivery-integrity.json`); builds, WAVs and the isolated checkout stay in the auditor's `tmp/`, not archived | – | – | n/a |
| 2026-11-03 C-01 zero-pad reference, [`2026-11-03-C01-zero-pad-aa379db/`](2026-11-03-C01-zero-pad-aa379db/) | `aa379db` | text-only delivery (bilingual preregistered design and reports, runner, full-precision values, CLI outputs, controls, logs and integrity manifest); C/Rust builds, WAVs and the isolated snapshot stay in `tmp/`, not archived; strict total-loudness gate failed, no closure | – | – | n/a |
| 2026-11-03 C-01 tail root cause, [`2026-11-03-C01-tail-root-cause-aa379db/`](2026-11-03-C01-tail-root-cause-aa379db/) | `aa379db` | separate text-only diagnostic delivery; bitwise baseline/replay controls and ordered stage substitutions quantify four tail discrepancies; removing rounding alone does not meet 1e-14; no production change or C-01 closure; raw stage arrays and builds remain in `tmp/` | – | – | n/a |
| 2026-11-03 C-01 cross-analysis (Claude, not Astra), [`2026-11-03-C01-cross-analysis-aa379db/`](2026-11-03-C01-cross-analysis-aa379db/) | `aa379db` | independent reproduction of the two Astra rounds over their stage arrays (bitwise Python ports of the C and Rust slope stages); closes both residuals: the slope residual is the dropped last-cell remainder (F-05, inherited from MoSQITo) plus C float32 constants, the main residual is C float32 constants; closure ≤1.4e-14 per frame with 0.22 or 0.24; band-0 wrap of the public `calc_slopes` recorded as F-06; feeds the [slope-alignment decision](../C01-F03-SLOPE-ALIGNMENT-DECISION-2026-11-03.md) | – | – | n/a |
| 2026-11-03 F-03 coefficient hypothesis, [`2026-11-03-F03-coefficient-hypothesis-aa379db/`](2026-11-03-F03-coefficient-hypothesis-aa379db/) | `aa379db` | research delivery (bilingual design and reports, `numeric.c`, isolation diffs, `results.json`, `run-log.json`, sources, integrity manifest); exact-arithmetic and C/Python/Rust cross-checks do not support "0.24 compensates floating-point or layout error"; the ISO Table A.9 cell itself stays PENDING; no table change | – | – | n/a |
| 2026-11-04 release 0.4.0 pre-push acceptance, [`2026-11-04-release-0.4.0-fca4ccd/`](2026-11-04-release-0.4.0-fca4ccd/) | `fca4ccd` | text-only delivery (bilingual reports, harness sources, logs, `results.json`, `delivery-integrity.json`); 68 files are CRLF and the folder is marked `-text` in `.gitattributes` so the manifest holds on checkout; builds, WAVs, golden-c data and isolated archives stay in `tmp/` | – | – | n/a |
| 2026-11-05 0.4.0 performance and Annex B conformance (Claude, not Astra), [`2026-11-05-perf-compliance-118322f/`](2026-11-05-perf-compliance-118322f/) | `118322f` (`v0.4.0`), baseline `aa379db` (`v0.3.1`) | text-only delivery (bilingual report, stage harness, Criterion runner and 12 logs, binding A/B, compliance script and results, artifact hashes, integrity manifest); end-to-end change within noise except +2% single-thread batch; 73,116 / 73,116 Annex B points pass, Nmax / N5 diagnostics within max(0.1, 5%); worktrees, builds and wheels stay in `tmp/` | – | – | n/a |

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
