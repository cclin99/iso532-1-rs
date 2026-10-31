# Verification brief: F-03 option B, lineage of the 0.24 value (AARAE 2015 / 2014 C)

> 對照／Pair: [中文版](2026-11-01-F03-B-aarae-lineage.zh-TW.md) · source: zh · synced 2026-11-01

For: Astra (`gpt-6-astra`). Issued 2026-11-01 (Asia/Taipei) by the main agent on the user's decision ("F-03 加做選項 B"). Source-tracing round; no numeric acceptance, no program change.

## 1. Question

`USL[12][4]` (zero-based; MATLAB/BASIC `USL(13,5)`; the cell for `0.300 ≤ N′ < 0.420`, critical band index 4) is `0.24` in this repository, MoSQITo 1.2.1 and SQAT (v1.0, v1.3, main), and `0.22f` in the archived official ISO 532-1 Annex A C program (SHA-256 `a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491`), the 1991 Zwicker et al. BASIC listing and MetaSona. SQAT states its lineage as "2014 Annex A C program → 2015 AARAE MATLAB implementation (Ella Manor) → 2023 SQAT". Two hypotheses are open:

- H1: the 2014 C program carried `0.24` and the archived C attachment is a later version (which would mean the C attachment was updated, possibly with the 2017-11 Table A.9 correction);
- H2: the 2014 C program carried `0.22` and the value changed in the AARAE transcription (or later).

Decide between H1, H2, or "undecidable with public sources", with evidence.

## 2. Scope

1. Locate the AARAE loudness analyser source (Ella Manor, 2015). Known public repositories: `densilcabrera/aarae` and `densilcabrera/aarae-source-old---please-use-aarae-for-current-repository-` on GitHub. Pin the commit, file path and line of the USL table; record the value of the target cell and the surrounding row; record the header comments that name the C source and its date.
2. If the AARAE source names or bundles the "2014 ISO 532-1 C program", pin it (file, commit, hash) and compare its USL table and any version/date identifiers with the archived official C (`ISO_532-1.c`, hash above). Report every differing cell of `USL`, not only `[12][4]`.
3. MoSQITo: pin the commit and file where the USL table entered the project and whether its comment names a source (C program, AARAE, paper). Do not re-verify the whole table; the target row and the cited source are enough.
4. SQAT: confirm or refute, from the pinned AARAE file, SQAT's statement that it derives from AARAE (one line-level comparison of the USL row is sufficient).
5. Optional, only if found on the way: any issue, commit message or discussion in these projects that mentions the 2017-11 Table A.9 correction.

Out of scope: purchasing or quoting the ISO text; changing `tables.rs`, goldens or any program; re-running numeric tests; treating any implementation value as the normative Table A.9 value.

## 3. Rules of evidence

- Every claim is pinned to a commit hash, file path and line number, or to a file SHA-256 for downloaded sources. Resolve `main`/tags to commits before reading.
- "Not found" is reported as a search result with the queries used, never as "does not exist".
- Implementation lineage (what a program contains) is kept separate from the normative value (what Table A.9 says). The gate for changing `USL[12][4]` stays as defined in `docs/修正報告2.md` §15.4; this round cannot close it.
- No paid or mirrored standard text is downloaded or quoted. Public code repositories and published papers are fine.

## 4. Delivery

- Folder: `docs/verification/2026-11-01-F03-B-lineage-<tested commit>/` where `<tested commit>` is `git rev-parse --short HEAD` at the time of the round; never overwrite an earlier folder.
- Files: `report.md` (Traditional Chinese) and `report.en.md` (English), same structure and numbers; `sources.md` (pinned URLs, commits, hashes); `delivery-check.md`.
- Before handing over: `python tools/redact_paths.py <folder>` then `python tools/redact_paths.py --check <folder>`; record the output, including any skipped files or warnings, in `delivery-check.md`. Only UTF-8 text files in the folder; no binaries, no PDF copies of standards.
- Verdict vocabulary: H1 / H2 / UNDECIDABLE, each with the evidence that supports and the evidence that limits it.

## 5. Context files

- `docs/F03-USL12-4-STATUS-2026-10-31.md` (and `.zh-TW.md`): status after the three rounds of 2026-10-31.
- `docs/verification/2026-10-31-F03-authority-d623d32/`, `…-sensitivity-d623d32/`, `…-SQAT-d623d32/`: the earlier deliveries.
- `docs/修正報告2.md` §15: the original F-03 record and the change gate.
