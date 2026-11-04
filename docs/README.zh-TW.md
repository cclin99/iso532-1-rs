# 文件索引

> 對照／Pair: [English](README.md) · 來源：zh · 同步 2026-11-01

語言規則見 `docs/DOCUMENTATION-LANGUAGE-POLICY.zh-TW.md`。對照文件以 `NAME.md`（英文）與 `NAME.zh-TW.md`（繁體中文）成對存在，結構與數字完全相同。`python tools/doc_pairs.py --check` 檢查配對；`--list` 列出即時狀態。下表日期為該配對的「同步」日期。

## 從這裡開始

| 文件 | 內容 | en | zh |
|---|---|---|---|
| [`../README.md`](../README.md) | 專案 README：範圍、安裝、API、證據、差異 | yes | [yes](../README.zh-TW.md) |
| [`ROADMAP.md`](ROADMAP.md) | 分階段路線圖與延後項目（R2 穩態 IsoReference 前端） | yes | [yes](ROADMAP.zh-TW.md) |
| [`RELEASE-CHECKLIST.md`](RELEASE-CHECKLIST.md) | 每次發布的步驤 | yes | [yes](RELEASE-CHECKLIST.zh-TW.md) |
| [`GOLDEN-REGEN-SOP.md`](GOLDEN-REGEN-SOP.md) | MoSQITo golden 資料如何重生與驗證 | yes | [yes](GOLDEN-REGEN-SOP.zh-TW.md) |
| [`DOCUMENTATION-LANGUAGE-POLICY.md`](DOCUMENTATION-LANGUAGE-POLICY.md) | 本語言政策、術語表、撰寫原則 | yes | [yes](DOCUMENTATION-LANGUAGE-POLICY.zh-TW.md) |

## 發布紀錄

| 文件 | 內容 | en | zh |
|---|---|---|---|
| [`RELEASE-0.4.0-2026-11-04.md`](RELEASE-0.4.0-2026-11-04.md) | 0.4.0：slope 階段依 Annex A（F-04～F-07）、分層門檻的 Annex A C golden、MoSQITo golden 改為相容性對照；獨立驗收 PARTIAL，無發布阻擋 | yes | [yes](RELEASE-0.4.0-2026-11-04.zh-TW.md) |
| [`RELEASE-0.3.1-2026-11-01.md`](RELEASE-0.3.1-2026-11-01.md) | 0.3.1：C-02 非有限輸入契約（錯誤碼 4）、C-01 輸出格線契約與測試、V-01 驗證器；數值不變 | yes | [yes](RELEASE-0.3.1-2026-11-01.zh-TW.md) |
| [`RELEASE-0.3.0-2026-10-31.md`](RELEASE-0.3.0-2026-10-31.md) | 0.3.0：發現 F-02（非線性衰減零初始狀態）、gates、產物、未結項目 | yes | [yes](RELEASE-0.3.0-2026-10-31.zh-TW.md) |
| [`RELEASE-0.2.0-2026-10-31.md`](RELEASE-0.2.0-2026-10-31.md) | 0.2.0：發現 F-01（低頻 DLL 列）、gates、產物 | yes | [yes](RELEASE-0.2.0-2026-10-31.zh-TW.md) |

## 發現、決策與狀態（2026-10-31 稽核週期）

| 編號 | 文件 | 狀態 | en | zh |
|---|---|---|---|---|
| F-01 | [`F01-LOW-FREQ-DLL-ROW-FIX-2026-10-31.md`](F01-LOW-FREQ-DLL-ROW-FIX-2026-10-31.md) | 已於 0.2.0 修正 | yes | [yes](F01-LOW-FREQ-DLL-ROW-FIX-2026-10-31.zh-TW.md) |
| F-02 | [`F02-NL-ZERO-INIT-2026-10-31.md`](F02-NL-ZERO-INIT-2026-10-31.md) | 已於 0.3.0 修正 | yes | [yes](F02-NL-ZERO-INIT-2026-10-31.zh-TW.md) |
| F-03 | [`F03-USL12-4-STATUS-2026-10-31.md`](F03-USL12-4-STATUS-2026-10-31.md) | 未結：`USL[12][4]` 0.24 vs 0.22，待 Table A.9；選項 B（血緣追溯）已於 2026-11-01 交辦 | yes | [yes](F03-USL12-4-STATUS-2026-10-31.zh-TW.md) |
| V-01 | [`V01-ANNEXB-VALIDATOR-2026-10-31.md`](V01-ANNEXB-VALIDATOR-2026-10-31.md) | 完成（僅測試），含浮點邊界根因 | yes | [yes](V01-ANNEXB-VALIDATOR-2026-10-31.zh-TW.md) |
| C-01 | [`C01-OUTPUT-LENGTH-DECISION-2026-10-31.md`](C01-OUTPUT-LENGTH-DECISION-2026-10-31.md) | 2026-11-01 已決：保留 ceil；契約凍結於文件與 `tests/output_grid.rs`；Astra 補零參考值輪已交辦 | yes | [yes](C01-OUTPUT-LENGTH-DECISION-2026-10-31.zh-TW.md) |
| C-02 | [`C02-NONFINITE-INPUT-2026-11-01.md`](C02-NONFINITE-INPUT-2026-11-01.md) | 完成：批次拒絕 NaN／Inf（錯誤碼 4），串流以 flag 回報 | yes | [yes](C02-NONFINITE-INPUT-2026-11-01.zh-TW.md) |
| — | [`ISO-ANNEXB-NUMERICAL-ERROR-2026-07-04.md`](ISO-ANNEXB-NUMERICAL-ERROR-2026-07-04.md) | 對 MoSQITo 與 Annex B 的數值殘差（含 2026-10-31 容差更正註記） | yes | [yes](ISO-ANNEXB-NUMERICAL-ERROR-2026-07-04.zh-TW.md) |

## 設計文件

| 文件 | 內容 | en | zh |
|---|---|---|---|
| [`DESIGN-DEVELOPMENT-2026-07-04.md`](DESIGN-DEVELOPMENT-2026-07-04.md) | 架構審查：誤差量化、效能、穩定性、隱藏缺陷、擴充性 | yes | [yes](DESIGN-DEVELOPMENT-2026-07-04.zh-TW.md) |
| [`SYSTEM-DESIGN-QA-2026-07-06.md`](SYSTEM-DESIGN-QA-2026-07-06.md) | 系統設計問答 | yes | [yes](SYSTEM-DESIGN-QA-2026-07-06.zh-TW.md) |
| [`MOSQITO-VS-ISO-BASELINE-STRATEGY-2026-07-05.md`](MOSQITO-VS-ISO-BASELINE-STRATEGY-2026-07-05.md) | 為何 MoSQITo golden 與 ISO Annex B 維持兩條獨立基準 | yes | [yes](MOSQITO-VS-ISO-BASELINE-STRATEGY-2026-07-05.zh-TW.md) |
| [`ARCH-EVAL-REPO-SPLIT-2026-07-18.md`](ARCH-EVAL-REPO-SPLIT-2026-07-18.md) | engine／panel 雙 repo 決策 | yes | [yes](ARCH-EVAL-REPO-SPLIT-2026-07-18.zh-TW.md) |
| [`CI-HASH-GATE-DEBUG-2026-07-10.md`](CI-HASH-GATE-DEBUG-2026-07-10.md) | 凍結 hash CI gate 的除錯過程 | yes | [yes](CI-HASH-GATE-DEBUG-2026-07-10.zh-TW.md) |
| [`PLAN-TIMING-ANALYSIS-2026-07-18.md`](PLAN-TIMING-ANALYSIS-2026-07-18.md) | 計畫各階段時程分析 | yes | [yes](PLAN-TIMING-ANALYSIS-2026-07-18.zh-TW.md) |

## 獨立驗證（證據，保留原文語言）

| 文件 | 內容 | 語言 |
|---|---|---|
| [`verification/README.md`](verification/README.md) | 所有驗證輪次、證據封存、去識別化規則、稽核員交辦簡報的索引 | en |
| [`修正報告.md`](修正報告.md) | 2026-10-31 稽核第一部分（修正前狀態、方法） | zh |
| [`修正報告2.md`](修正報告2.md) | 2026-10-31 稽核第二部分：優先序 §12、F-01 再驗證 §14、F-03 §15、V-01 規格 §15.5 | zh |
| [`修正後獨立驗證報告.md`](修正後獨立驗證報告.md) | F-01 修正後獨立驗證（`3dc420c`、`6aea8b3`） | zh |
| `verification/2026-10-31-F02-5450d39/` | F-02 驗證：範圍內 PASS | zh |
| `verification/2026-10-31-F03-sensitivity-d623d32/` | F-03：測試無法分辨 0.22 與 0.24 | zh |
| `verification/2026-10-31-F03-authority-d623d32/` | F-03：Table A.9 確認於 2017-11 更正，但不知哪一格；1991 論文為 0.22 | zh |
| `verification/2026-10-31-F03-SQAT-d623d32/` | F-03：SQAT 所有版本皆為 0.24 | zh |
| [`verification/briefs/2026-11-01-F03-B-aarae-lineage.zh-TW.md`](verification/briefs/2026-11-01-F03-B-aarae-lineage.zh-TW.md) | F-03 選項 B 交辦簡報 | en + zh |
| [`verification/briefs/2026-11-01-C01-zero-pad-reference.zh-TW.md`](verification/briefs/2026-11-01-C01-zero-pad-reference.zh-TW.md) | C-01 尾端點官方 C 參考值交辦簡報 | en + zh |
| [`verification/briefs/2026-11-01-release-0.3.1-acceptance.zh-TW.md`](verification/briefs/2026-11-01-release-0.3.1-acceptance.zh-TW.md) | release commit `30e4279` 打 tag 前的驗收交辦簡報 | en + zh |
| [`verification/briefs/2026-11-04-release-0.4.0-acceptance.zh-TW.md`](verification/briefs/2026-11-04-release-0.4.0-acceptance.zh-TW.md) | 0.4.0 候選 `fca4ccd` 推送與打 tag 前的驗收交辦簡報 | en + zh |
| [`verification/2026-11-02-release-0.3.1-30e4279/report.md`](verification/2026-11-02-release-0.3.1-30e4279/report.md) | 0.3.1 在 `30e4279` 的打 tag 前驗收：ACCEPT，8／8 項通過 | en + zh |
| [`verification/2026-11-04-release-0.4.0-fca4ccd/report.md`](verification/2026-11-04-release-0.4.0-fca4ccd/report.md) | 0.4.0 在 `fca4ccd` 的推送前驗收：PARTIAL，7／9 項通過，無數值或 API 阻擋（串流沒有比響度可驗；commit 表漏列已補） | en + zh |

## 歷史審查紀錄（已結輪次；翻譯待辦 P3）

以下為單行英文摘要；文件本身為中文。

| 文件 | 摘要 |
|---|---|
| `ARCHITECTURE-PERFORMANCE-RISK-REPORT-2026-07-10.md` | R4 band-parallel 階段的架構與效能風險報告 |
| `R3-REVIEW-2026-07-11.md`、`R3-FIXES-REVIEW-2026-07-11.md`、`R3-REVIEW-FIXES-IMPLEMENTATION-2026-07-11.md` | R3（golden 鏈、FFI、Python）審查、修正審查與實作紀錄 |
| `R4-REVIEW-CLOSEOUT-2026-07-10.md` | R4 band-parallel 結案 |
| `R5-REVIEW-FIXES-2026-07-17.md`、`R5-REVIEW-2-FIXES-2026-07-17.md`、`R5-REVIEW-3-FIXES-2026-07-18.md`、`R5-REVIEW-FIXES-IMPLEMENTATION-2026-07-17.md` | R5 串流 API 審查輪次與修正 |
| `iso532-1-rs-code-review-remediation.md` | 程式碼審查補救紀錄 |

## 工作計畫（單一語言，豁免）

`superpowers/plans/` 放主計畫（`2026-07-03-iso532-rust-avx.md`）、路線圖主計畫，以及 `phases/` 下各階段的 Codex 計畫（含 2026-10-31 執行的 `phase-v01-annexb-validator.md`）。

## 翻譯待辦

| 優先序 | 項目 | 規則 |
|---|---|---|
| P1 | 2026-11-01 後無未結項 | 所有使用者面向文件皆成對 |
| P2 | 無 | 設計文件皆成對 |
| P3 | 上述歷史審查紀錄 | 僅英文摘要行，除非另行要求 |
