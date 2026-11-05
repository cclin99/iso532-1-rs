# 驗證交辦簡報：各實作對 Annex B 的誤差，以及 `USL[12][4]` 這一格的貢獻

> 對照／Pair: [English](2026-11-05-F03-implementation-errors.md) · 來源：zh · 同步 2026-11-05

對象：Astra（`gpt-6-astra`）。2026-11-05（Asia/Taipei）由主代理依使用者要求發出；主代理同時另做一輪，兩者互不參考。驗證輪；不改程式。

## 1. 問題

ISO 532-1:2017 的 `USL[12][4]`（上側斜率表第 13 列第 5 欄，zero-based）在不同實作中有兩種值：官方 Annex A C 程式為 `0.22f`；MoSQITo 1.2.1、SQAT 與本專案 `iso532` 0.4.0 為 0.24。請獨立量測：

1. 官方 C 程式、SQAT、MoSQITo、`iso532` 對 Annex B 工作簿參考值的誤差各是多少。
2. 其中有多少來自這一格：每個實作都以「原本的值」與「只改這一格的另一個值」各跑一次。
3. 主代理在 [`docs/verification/2026-11-05-F03-workbook-provenance-118322f/`](../2026-11-05-F03-workbook-provenance-118322f/report.md) 的宣稱是否成立：Annex B 工作簿是由未修改的官方 C 程式（0.22f）以「滿刻度 1.0 = 2√2 Pa」換算產生的；在兩版官方 C 差距 ≥ 2e-4 sone 的 12,287 點中，工作簿等於 0.22 版 11,174 點、等於 0.24 版 0 點。

背景（可讀，但數字必須自行重現，不得沿用主代理的輸出檔）：
- 換算慣例：[`2026-11-05-annexb-bias-118322f/`](../2026-11-05-annexb-bias-118322f/report.md)。校準檔比標示的 60 dB 低 0.0226 dB；以校準檔換算，響度會一致偏高約 0.15%。
- ZWST 前端：[`2026-11-05-zwst-root-cause-118322f/`](../2026-11-05-zwst-root-cause-118322f/report.md)。
- F-03 先前各輪：`docs/F03-USL12-4-STATUS-2026-10-31.zh-TW.md`。

## 2. 範圍

1. **凍結。** 受驗快照為 `493fd59`（`iso532` crate 與 `v0.4.0` = `118322f` 位元相同）；從隔離 checkout（`git worktree add` 或 `git archive`）建置，不要用主工作樹。記錄工具鏈：rustc、Python、NumPy、SciPy、MSVC、MATLAB 或 Octave 的版本。
2. **官方素材。** ISO 原始檔在 `tmp/c01-material/official/`。逐檔記錄 SHA-256：`ISO_532-1.c`（應為 `a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491`）、`ISO_532-1_main.c`、`ISO_532-1_helper.c`、三本工作簿、24 個 WAV、`Test signal 1.txt`、校準檔。
3. **輸入。** 兩種換算都要做，結果分開回報：
   - (a) `int16 / 32768 × 2√2` Pa；
   - (b) 依官方 `ISO_532-1_main.c` 的作法，用 Annex C 校準檔的全段均方值，以 60 dB 計算係數。
   官方 CLI 吃浮點 WAV 時不需要校準檔；整數 WAV 需要校準檔。輸入檔的 hash 都要記錄。
4. **實作與變體**（每一項都要「原本的值」與「只改一格」兩版；變體的建法要可以重現，並交付 diff）：
   - 官方 C：自己用 MSVC x64 `/O2 /fp:precise` 從原始碼建 CLI。未修改版 = 0.22f；變體只把 `USL[12][4]` 改成 0.24f（替換後 SHA-256 應為 `739af24dee118027cb419fcdb051d8b56b274211d986140d66d7ff4b9d52a7e9`）。
   - SQAT v2.0：GitHub `ggrecow/SQAT` tag `v2.0`（應解析為 `94f489c053d1366da05d5e62838c3f54ac7715c3`），`Loudness_ISO532_1`。原本 = 0.24；變體把 `USL(13,5)` 改成 0.22。用 MATLAB 或 GNU Octave 執行，記錄版本與相依套件。**若兩者都無法執行，這一項標為 BLOCKED，並寫明原因；不要自行改寫或移植 SQAT。**
   - MoSQITo 1.2.1：用固定版本（記錄套件或原始檔 hash）。原本 = 0.24；變體只改 `_calc_slopes` 裡 `usl` 那一格成 0.22。不得修改已安裝的檔案，請在隔離副本或以執行期替換的方式處理。
   - `iso532` 0.4.0：原本 = 0.24；變體只改 `iso532/src/tables.rs` 那一格成 0.22，在隔離副本中建置。
   - 負對照：至少一個實作再跑一個明顯錯誤的值（例如 0.30），確認判定方法能分辨。
5. **比對對象與指標**（工作簿為參考；時變訊號用工作簿時間點；穩態用 B8 的 N 與 G8:G247 的 N′）：
   - 穩態訊號 1–5：N 的誤差、240 格 N′ 的最大絕對誤差。訊號 1 是 1/3 倍頻程位準輸入，用各實作的對應入口，沒有入口就寫「不適用」。
   - 時變訊號 6–25：N(t) 的最大與中位絕對誤差、相對誤差；訊號 6–13 另外比工作簿指定 Bark 的 N′(t)；Nmax；N5 依工作簿公式的列範圍計算（注意訊號 12、13 的公式引用 E 欄）。
   - 超出 `max(0.1, 0.05·|ref|)` 的點數（零例外，不放寬）。
   - 「決定性點」：兩版官方 C 差距 ≥ 2e-4 sone 的點。在這些點上回報每個實作兩個變體的誤差，以及工作簿等於、或比較接近哪一版的點數。
   - 這一格的單獨影響：每個實作「原本 − 變體」的最大絕對差與受影響的點數。
   - 各實作之間的差異（例如 SQAT 對官方 C、MoSQITo 對官方 C），用來區分「這一格」與「其他實作差異」。
6. **輸出精度。** 官方 CLI 輸出到小數第四位，這會限制解析度，請說明你的「完全相同」判準。
7. **結論。** 對第 1 節的三個問題分別給出答案。與主代理宣稱的任何差異一律寫「發現」。

範圍外：修改產品程式或 golden；購買標準；判定 Table A.9 的正式值（本輪只量測實作與參考數據的關係）。

## 3. 證據規則

- 每個數字都由交付資料夾內的腳本產生，且能從凍結 commit、記錄的工具鏈與輸入 hash 重現。harness 原始碼要一併交付（`.c`、`.rs`、`.m` 以 `.txt` 副檔名交付）。
- 第三方原始碼（SQAT 是 GPL-3.0、MoSQITo、ISO 素材）不收錄全文，只記版本、hash 與引用的行號；只改一格的 diff 可以交付。
- 每個項目回報 PASS／FAIL／BLOCKED／SKIPPED／PARTIAL；缺口就保留為缺口。

## 4. 交付

- 資料夾：`docs/verification/<YYYY-MM-DD>-F03-implementation-errors-493fd59/`，日期用交付日（Asia/Taipei）；不得覆蓋舊資料夾。
- 檔案：`report.md`（繁體中文）與 `report.en.md`，結構與數字相同；`results.json`（每個實作 × 變體 × 訊號的指標、決定性點的統計、hash）；harness 原始碼與執行腳本；`delivery-check.md`；去識別化後才產生、並明確排除自身的 `delivery-integrity.json`。
- 交付前：先執行 `python tools/redact_paths.py <資料夾>`，再執行 `--check`；把輸出（包括 skipped 與警告）記在 `delivery-check.md`。工具沒有涵蓋的副檔名和非 UTF-8 檔，要逐檔另外檢查；刪除 `__pycache__`。資料夾只放 UTF-8 文字檔；WAV、執行檔、CSV 大檔不進庫，只記 hash。原始輸入、binary、受驗來源的 hash 保留原本的意義，不要宣稱去識別化後的副本跟原檔位元相同。
- 檔案行尾用 LF；若有 CRLF，要在 `delivery-check.md` 說明怎麼處理，並確認 `delivery-integrity.json` 對應的是最後進庫的位元。
- 交付不含 commit 和 push。主代理會 stage 交付資料夾、重跑去識別化檢查，再提交。
