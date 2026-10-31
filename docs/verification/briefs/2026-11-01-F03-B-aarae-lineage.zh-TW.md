# 驗證交辦：F-03 選項 B，0.24 這個值的沿革（AARAE 2015／2014 C）

> 對照／Pair: [English](2026-11-01-F03-B-aarae-lineage.md) · 來源：zh · 同步 2026-11-01

交辦對象：Astra（`gpt-6-astra`）。2026-11-01（Asia/Taipei）由主代理依使用者決定（「F-03 加做選項 B」）發出。本輪是來源追查，不做數值驗收、不改程式。

## 1. 問題

`USL[12][4]`（zero-based；MATLAB／BASIC 的 `USL(13,5)`；對應 `0.300 ≤ N′ < 0.420`、critical band index 4 的那一格）在本 repo、MoSQITo 1.2.1 與 SQAT（v1.0、v1.3、main）是 `0.24`，在保存的官方 ISO 532-1 Annex A C 程式（SHA-256 `a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491`）、1991 Zwicker 等人的 BASIC 原刊與 MetaSona 是 `0.22f`。SQAT 自述來源鏈為「2014 Annex A C 程式 → 2015 AARAE MATLAB 實作（Ella Manor）→ 2023 SQAT」。待解的兩個假說：

- H1：2014 的 C 程式本來就是 `0.24`，保存的 C 附件是較新版本（意味 C 附件曾更新，可能與 2017-11 的 Table A.9 更正有關）；
- H2：2014 的 C 程式是 `0.22`，值是在 AARAE 轉寫時（或之後）改變的。

請以證據判定 H1、H2，或「公開來源無法判定」。

## 2. 範圍

1. 找到 AARAE 的響度分析器原始碼（Ella Manor，2015）。已知公開 repo：GitHub 的 `densilcabrera/aarae` 與 `densilcabrera/aarae-source-old---please-use-aarae-for-current-repository-`。固定 commit、檔案路徑與 USL 表所在行；記錄目標格與整列的值；記錄檔頭註解中提到的 C 來源及其日期。
2. 若 AARAE 原始碼有提到或附帶「2014 ISO 532-1 C 程式」，固定它（檔案、commit、hash），把它的 USL 表與任何版本／日期識別和保存的官方 C（`ISO_532-1.c`，hash 如上）比對。報告 `USL` 所有不同的格，不只 `[12][4]`。
3. MoSQITo：固定 USL 表進入專案的 commit 與檔案，以及其註解是否指明來源（C 程式、AARAE、論文）。不需重驗整表，目標列與引用來源即可。
4. SQAT：以固定的 AARAE 檔案確認或否定 SQAT「源於 AARAE」的陳述（USL 該列逐行比對一次即可）。
5. 選做，順路看到才做：這些專案的 issue、commit 訊息或討論中任何提到 2017-11 Table A.9 更正的內容。

範圍外：購買或引用 ISO 全文；改 `tables.rs`、golden 或任何程式；重跑數值測試；把任何實作值當作 Table A.9 的正式值。

## 3. 證據規則

- 每個主張都要釘到 commit hash、檔案路徑與行號，下載的來源則附檔案 SHA-256。讀取前先把 `main`／tag 解析成 commit。
- 「找不到」要寫成搜尋結果並附所用查詢，不能寫成「不存在」。
- 實作沿革（程式裡是什麼）與正式值（Table A.9 寫什麼）分開陳述。改 `USL[12][4]` 的門檻仍依 `docs/修正報告2.md` §15.4；本輪不能關閉它。
- 不下載、不引用付費或鏡像的標準全文。公開程式碼 repo 與已發表論文可以。

## 4. 交付

- 資料夾：`docs/verification/2026-11-01-F03-B-lineage-<受驗 commit>/`，`<受驗 commit>` 為本輪當時的 `git rev-parse --short HEAD`；不得覆蓋舊資料夾。
- 檔案：`report.md`（繁體中文）與 `report.en.md`（英文），結構與數字相同；`sources.md`（固定 URL、commit、hash）；`delivery-check.md`。
- 交付前：`python tools/redact_paths.py <資料夾>`，再 `python tools/redact_paths.py --check <資料夾>`；把輸出（含任何 skipped 或警告）記在 `delivery-check.md`。資料夾內只放 UTF-8 文字檔；不放 binary、不放標準的 PDF 副本。
- 判定用語：H1／H2／UNDECIDABLE，各自附支持的證據與限制。

## 5. 背景檔案

- `docs/F03-USL12-4-STATUS-2026-10-31.md`（與 `.zh-TW.md`）：2026-10-31 三輪之後的狀態。
- `docs/verification/2026-10-31-F03-authority-d623d32/`、`…-sensitivity-d623d32/`、`…-SQAT-d623d32/`：先前的交付。
- `docs/修正報告2.md` §15：F-03 的原始紀錄與改表門檻。
