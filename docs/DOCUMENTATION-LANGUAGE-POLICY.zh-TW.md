# 文件語言政策

> 對照／Pair: [English](DOCUMENTATION-LANGUAGE-POLICY.md) · 來源：en · 同步 2026-11-01

自 2026-11-01 起生效，適用於本 repo 的所有 Markdown 文件。

## 1. 為什麼

本專案以繁體中文開發，使用者有只讀英文的，也有只讀中文的。決策備忘、release 紀錄與契約文件必須讓兩群人都能用，而且數字、識別碼與結論完全相同。只有單一語言的文件，對另一半讀者來說等於沒有文件。

## 2. 配對規則

**配對類**的每份文件都以同一個主檔名存在兩個檔案：

| 檔案 | 語言 | 角色 |
|---|---|---|
| `NAME.md` | 英文 | 程式識別碼、檔名、數字以此為準 |
| `NAME.zh-TW.md` | 繁體中文（台灣用語） | 使用者的決策與推理以此為準 |

沿用既有的 `README.md`／`README.zh-TW.md` 慣例。兩個檔案：

- 章節編號、表格與數字完全相同，所以「§4.1」或「§2 的表」在任一檔都能對上；
- 標題下一行放對照行：
  - 英文：`> 對照／Pair: [中文版](NAME.zh-TW.md) · source: en|zh · synced YYYY-MM-DD`
  - 中文：`> 對照／Pair: [English](NAME.md) · 來源：en|zh · 同步 YYYY-MM-DD`
- 一起更新。只改一邊視為未完成；兩邊再次一致時更新 `同步` 日期。

`來源` 記錄文件原本用哪種語言寫成；另一檔是在同步日期時的譯文。兩邊敘述不一致時以來源語言為準。數字、hash、commit、識別碼在兩邊永遠不得不同。

## 3. 分類

| 類別 | 例子 | 規則 |
|---|---|---|
| **配對（必須）** | `README`、release 紀錄（`RELEASE-*`）、`RELEASE-CHECKLIST`、SOP（`GOLDEN-REGEN-SOP`）、`ROADMAP`、發現紀錄（`F01-*`、`F02-*`、`F03-*`）、決策與狀態備忘（`C01-*`、`V01-*`）、設計文件、契約文件、本政策 | commit 前兩檔都要存在；`tools/doc_pairs.py --check` 通過 |
| **驗證交付** | `docs/verification/<日期>-<議題>-<commit>/`、`修正報告.md`、`修正報告2.md`、`修正後獨立驗證報告.md` | 驗證方原文是證據，不得就地改寫或翻譯。自 2026-10-31 起驗證方在同一資料夾交付 `report.md`（中文）與 `report.en.md`（英文），兩者皆由驗證方撰寫。更早的交付只在 `docs/verification/README.md` 補一列英文摘要 |
| **工作計畫** | `docs/superpowers/plans/**`（Codex phase 計畫、主計畫）、`docs/verification/briefs/` 的驗證交辦 | 可單一語言；交辦驗證方的 brief 需配對，因為驗證方的產出必須雙語 |
| **生態慣例檔** | `CHANGELOG.md`、`CITATION.cff`、`SECURITY.md`、`THIRD_PARTY_NOTICES.md`、程式註解、commit 訊息、C header | 英文（程式註解可用任一語言） |
| **歷史審查** | `R3-*`、`R4-*`、`R5-*`、`ARCHITECTURE-PERFORMANCE-RISK-*`、`iso532-1-rs-code-review-remediation` | 已結案審查輪的凍結紀錄；翻譯列入 backlog、非必須；在 `docs/README.md` 以一行英文摘要列出 |

## 4. 英文寫作原則

1. 結論先行，再證據，再未決問題。一句一個意思。
2. 使用 ISO 532-1 術語並保持一致（§6 詞彙表）。不自創同義詞。
3. 程式識別碼、檔名、commit hash、旗標、錯誤碼一律以反引號逐字保留，不翻譯。
4. 明寫證據界線：量了什麼、在哪個快照、用什麼工具、沒查什麼。「範圍內 PASS」不等於「符合標準」。
5. 對 MoSQITo 的差異寫 “finding” 與 “current judgment”，不寫 “bug”、“error”（F-01 以來的專案規則：過程發現與現有判斷）。
6. 日期用 ISO 8601，必要時標時區（Asia/Taipei）。數字帶單位（sone、sone/Bark、dB SPL、ms、samples）。
7. 平行事實用表格，論證用文字。不加裝飾性措辭。

## 5. 中文寫作原則

1. 繁體中文、台灣用語；專有名詞第一次出現時附英文原文，之後可只用中文。
2. 數字、單位、識別碼、檔名、commit、旗標與錯誤碼與英文版逐字相同。
3. 結論先行；證據界線寫清楚（量了什麼、在哪個快照、用什麼工具、沒查什麼）。
4. 對 MoSQITo 的差異一律寫「發現」「目前判斷」，不寫「bug」「錯誤」。
5. 不把程式名稱、檔名翻成中文。

## 6. 詞彙表

| 中文 | English | 備註 |
|---|---|---|
| 響度 | loudness, `N` | 單位 sone |
| 比響度 | specific loudness, `N′` | 單位 sone/Bark |
| 臨界頻帶率 | critical-band rate | 單位 Bark，240 格、每格 0.1 Bark |
| 三分之一倍頻程頻帶位準 | third-octave band level | 28 個頻帶，dB SPL |
| 穩態響度 | stationary loudness (ZWST) | ISO 532-1 §5 |
| 時變響度 | time-varying loudness (ZWTV) | ISO 532-1 §6 |
| 自由場／擴散場 | free field / diffuse field | `FieldType::Free`／`Diffuse` |
| 主響度 | main loudness, core loudness | 21 個頻帶 |
| 非線性時間衰減 | nonlinear temporal decay | `nl_loudness`，Annex A `f_nl` |
| 時間加權 | temporal weighting | 0.47·LP(3.5 ms) + 0.53·LP(70 ms) |
| 低頻修正 | low-frequency correction（RAP／DLL 表） | 發現 F-01 |
| 零狀態初始化 | zero-state initialisation | `NlInit::Zero`，發現 F-02 |
| 上斜率表 | upper-slope table `USL` | Table A.9，發現 F-03 |
| 參考程式 | Annex A reference program (C) | `ISO_532-1.c` |
| 測試訊號／參考值 | Annex B test signals / reference values | 工作簿，25 個訊號 |
| 容差 | tolerance | 逐點 `max(0.1, 0.05·|reference|)` |
| 例外 | exception（超出容差） | Annex B 的 1 % 條款未實作 |
| 批次／串流 | batch / stream | `loudness_zwtv`／`ZwtvStream` |
| 輸出格線 | output grid | 2 ms，`zwtv_out_frames` |
| 前綴因果性 | prefix causality | 前段結果永不受後段樣本影響 |
| 獨立驗證 | independent verification | `docs/verification/` 下的 Astra 輪次 |
| 去識別化 | redaction（工作站路徑） | `tools/redact_paths.py` |
| 發現／目前判斷 | finding / current judgment | 對 MoSQITo 差異不寫 “bug” |

## 7. 索引與 backlog

`docs/README.md`（與 `docs/README.zh-TW.md` 配對）列出每份文件的類別、現有語言、同步日期；未配對的文件標 backlog 優先序：

- **P1**：仍缺對照版的使用者文件；目標：下一個 release 前補齊。
- **P2**：已結案審查輪的設計文件；動到時再翻。
- **P3**：歷史審查紀錄；只給一行英文摘要，除非有人要求。

## 8. 流程

1. 新的配對文件：同一個 commit 寫完兩檔。若譯文由助理產生，作者 commit 前讀過；數字與識別碼以工具機械比對。
2. 修改配對文件：兩邊都改，更新 `同步` 日期。
3. release 前 `python tools/doc_pairs.py --check` 必須印出 `ok`：它檢查每份配對文件兩檔皆在、對照行相符，且 `docs/` 下沒有豁免清單以外的未配對檔。
4. 交辦驗證方的 brief 要寫明：「交付 `report.md` 與 `report.en.md`，結構與數字相同」。
