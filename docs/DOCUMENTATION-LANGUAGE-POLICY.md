# Documentation language policy

> 對照／Pair: [中文版](DOCUMENTATION-LANGUAGE-POLICY.zh-TW.md) · source: en · synced 2026-11-01

Effective 2026-11-01. Applies to every Markdown document in this repository.

## 1. Why

The project is developed in Traditional Chinese and used by people who read only English, or only Chinese. Decision memos, release records and contract documents must be usable by both groups, with identical numbers, identifiers and conclusions. A document that exists in one language only is, for half of the readers, not documentation.

## 2. Pairing rule

Every document in the **paired** category exists as two files with the same base name:

| file | language | role |
|---|---|---|
| `NAME.md` | English | canonical for code identifiers, file names, numbers |
| `NAME.zh-TW.md` | Traditional Chinese (Taiwan usage) | canonical for the user's decisions and reasoning |

This follows the existing `README.md` / `README.zh-TW.md` convention. Both files:

- carry the same section numbering, the same tables and the same numbers, so a reference such as "§4.1" or "table in §2" resolves in either file;
- start with a pair line right after the title:
  - English: `> 對照／Pair: [中文版](NAME.zh-TW.md) · source: en|zh · synced YYYY-MM-DD`
  - Chinese: `> 對照／Pair: [English](NAME.md) · 來源：en|zh · 同步 YYYY-MM-DD`
- are updated together. A change to one file without the other is incomplete; bump the `synced` date when both match again.

`source:` records which language the document was written in; the other file is a translation of it at the synced date. When the two disagree in prose, the source governs. Numbers, hashes, commit ids and code identifiers never differ between the two.

## 3. Categories

| category | examples | rule |
|---|---|---|
| **Paired (required)** | `README`, release records (`RELEASE-*`), `RELEASE-CHECKLIST`, SOPs (`GOLDEN-REGEN-SOP`), `ROADMAP`, finding records (`F01-*`, `F02-*`, `F03-*`), decision and status memos (`C01-*`, `V01-*`), design documents, contract documents, this policy | both files exist before the change is committed; `tools/doc_pairs.py --check` passes |
| **Verification deliveries** | `docs/verification/<date>-<topic>-<commit>/`, `修正報告.md`, `修正報告2.md`, `修正後獨立驗證報告.md` | the auditor's original text is evidence and is never rewritten or translated in place. From 2026-10-31 the auditor delivers `report.md` (Chinese) and `report.en.md` (English) in the same folder, both written by the auditor. Earlier deliveries get an English summary row in `docs/verification/README.md` only |
| **Working plans** | `docs/superpowers/plans/**` (Codex phase plans, master plans), verification briefs under `docs/verification/briefs/` | single language is acceptable; briefs to the auditor are paired because the auditor's output must be bilingual |
| **Ecosystem-convention files** | `CHANGELOG.md`, `CITATION.cff`, `SECURITY.md`, `THIRD_PARTY_NOTICES.md`, code comments, commit messages, the C header | English (code comments may be in either language) |
| **Historical reviews** | `R3-*`, `R4-*`, `R5-*`, `ARCHITECTURE-PERFORMANCE-RISK-*`, `iso532-1-rs-code-review-remediation` | frozen records of closed review rounds; translation is backlog, not required; listed with a one-line English summary in `docs/README.md` |

## 4. English writing principles

1. Lead with the conclusion, then the evidence, then the open questions. One idea per sentence.
2. Use ISO 532-1 terminology and keep it consistent (glossary in §6). Do not invent synonyms.
3. Keep code identifiers, file names, commit hashes, flags and error codes verbatim in backticks. Never translate them.
4. State the evidence boundary explicitly: what was measured, on which snapshot, with which tool, and what was not checked. "PASS within scope" is not "compliant".
5. For divergences from MoSQITo write "finding" and "current judgment", not "bug" or "error" (project rule since F-01: 過程發現與現有判斷).
6. Dates in ISO 8601 with the time zone when it matters (Asia/Taipei). Numbers with units (sone, sone/Bark, dB SPL, ms, samples).
7. Tables for parallel facts; prose for argument. No decorative wording.

## 5. Chinese writing principles

1. 繁體中文、台灣用語；專有名詞第一次出現時附英文原文，之後可只用中文。
2. 數字、單位、識別碼、檔名、commit、旗標與錯誤碼與英文版逐字相同。
3. 結論先行；證據界線寫清楚（量了什麼、在哪個快照、用什麼工具、沒查什麼）。
4. 對 MoSQITo 的差異一律寫「發現」「目前判斷」，不寫「bug」「錯誤」。
5. 不把程式名稱、檔名翻成中文。

## 6. Glossary

| 中文 | English | notes |
|---|---|---|
| 響度 | loudness, `N` | unit sone |
| 比響度 | specific loudness, `N′` | unit sone/Bark |
| 臨界頻帶率 | critical-band rate | unit Bark, 240 steps of 0.1 Bark |
| 三分之一倍頻程頻帶位準 | third-octave band level | 28 bands, dB SPL |
| 穩態響度 | stationary loudness (ZWST) | ISO 532-1 §5 |
| 時變響度 | time-varying loudness (ZWTV) | ISO 532-1 §6 |
| 自由場／擴散場 | free field / diffuse field | `FieldType::Free` / `Diffuse` |
| 主響度 | main loudness, core loudness | 21 bands |
| 非線性時間衰減 | nonlinear temporal decay | `nl_loudness`, Annex A `f_nl` |
| 時間加權 | temporal weighting | 0.47·LP(3.5 ms) + 0.53·LP(70 ms) |
| 低頻修正 | low-frequency correction (RAP/DLL tables) | finding F-01 |
| 零狀態初始化 | zero-state initialisation | `NlInit::Zero`, finding F-02 |
| 上斜率表 | upper-slope table `USL` | Table A.9, finding F-03 |
| 參考程式 | Annex A reference program (C) | `ISO_532-1.c` |
| 測試訊號／參考值 | Annex B test signals / reference values | workbook, 25 signals |
| 容差 | tolerance | `max(0.1, 0.05·|reference|)` per point |
| 例外 | exception (tolerance exceedance) | Annex B 1 % clause not implemented |
| 批次／串流 | batch / stream | `loudness_zwtv` / `ZwtvStream` |
| 輸出格線 | output grid | 2 ms, `zwtv_out_frames` |
| 前綴因果性 | prefix causality | result for a prefix never depends on later samples |
| 獨立驗證 | independent verification | Astra rounds under `docs/verification/` |
| 去識別化 | redaction (of workstation paths) | `tools/redact_paths.py` |
| 發現／目前判斷 | finding / current judgment | never "bug" for MoSQITo divergences |

## 7. Index and backlog

`docs/README.md` (paired with `docs/README.zh-TW.md`) lists every document with its category, the languages available, the synced date and, for unpaired documents, the backlog priority:

- **P1**: user-facing documents still missing a counterpart; target: next release.
- **P2**: design documents from closed review rounds; translate when touched.
- **P3**: historical review minutes; English summary line only unless requested.

## 8. Process

1. New paired document: write both files in the same commit. If the translation is produced by an assistant, the author reads it before committing; numbers and identifiers are diffed mechanically.
2. Change to a paired document: update both, bump `synced`.
3. `python tools/doc_pairs.py --check` must print `ok` before a release; it verifies that every paired document has both files with matching pair lines, and that no file under `docs/` outside the exempt lists is unpaired.
4. Verification briefs handed to the auditor state: "deliver `report.md` and `report.en.md`, same structure and numbers".
