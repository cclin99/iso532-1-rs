# 0.4.0 slope 階段對齊 Annex A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 依 `docs/C01-F03-SLOPE-ALIGNMENT-DECISION-2026-11-03.zh-TW.md` 的 D1–D5：移除 `calc_slopes` 的每幀捨入（F-04）、補回 band 最後格點之後的平台段（F-05）、加固 band-0 繞回（F-06）、把正確性 golden 改以官方 C 產生（門檻 1e-10）、更新文件與版號到 0.4.0。`USL[12][4]` 維持 0.24，本階段不動表格。

**Architecture:** 只改 `iso532/src/core/calc_slopes.rs` 的 `calc_slopes_impl`，批次、串流、SIMD 路徑都呼叫它，自動同步。新增 C golden 測試 `iso532/tests/golden_c.rs` 與產生工具 `tools/gen_golden_c.py`；既有 MoSQITo golden 測試改為容差。不新增公開 API、不改輸出格線、不改串流契約。

**Tech Stack:** Rust 2021；Python 3 + NumPy（golden 工具）；MSVC x64（只在產生 C golden 時需要，測試本身不需要）。

**實作者:** Claude Opus 5.5（本階段不交 Codex）；完成後由 Astra 獨立驗收，驗收簡報另出。

**上游依據:** 決策備忘 D1–D5；證據 `docs/verification/2026-11-03-C01-tail-root-cause-aa379db/`、`docs/verification/2026-11-03-C01-cross-analysis-aa379db/`（`sliver_check.py` 的 `rust_slopes_fixed` 是 F-05 的參考實作，Python）。不授權處理穩態前端、F-03 表格、Table A.9 取得。

---

## 先鎖定決策

### D-A. F-05 的修法 = 迴圈後補完 band，不是重寫演算法

`calc_slopes_impl` 的每 band 格點迴圈結束後，若 `mask_n1_bigger_nm` 仍為 true 且 `z2[zup_ea[i]-1] < ZUP[i]`，以 Annex A 的語意從 `(z1_aux, n1_aux)` 補完到 `ZUP[i]`：若 `r8(n1) <= r8(nm[i])` 補平台 `nm[i]*(ZUP[i]-z1)`；否則以 `get_rns_index(n1, true)` 取 USL 繼續斜率段直到 `ZUP[i]`（含夾到 ZUP 的最後一段），每段 `total += dz*(n1+n2)/2`。specific 陣列在該格點的值不變（它已由迴圈寫入）。參考實作：cross-analysis `sliver_check.py::rust_slopes_fixed` 的 `restoration` 區塊。

### D-B. F-04 = 刪除第 161–165 行，保留負值截斷

`total < 0 → 0` 保留（C 也有）。不加任何顯示捨入；若呼叫端要三位小數自己做。

### D-C. F-06 = band 0 不得讀 band 20

`i == 0` 時 `mask_n1_bigger_nm` 固定為 false（C 的 `N1 = 0` 起始語意），不再經 `prev_grid_index(0) = 239` 讀 `n2[239]`。此改動對所有經 pipeline 的輸入逐位元無影響（main loudness 固定 nm[20] = 0），用 hash gate 證明。

### D-D. C golden 的參考程式

官方 `ISO_532-1.c`（SHA-256 `a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491`）只替換 `USL[12][4]` 的 `0.22f` 為 `0.24f`，其餘不動；工具同時記錄原檔與替換版 hash、編譯器版本與旗標（`/O2 /fp:precise`）。wrapper 只呼叫 `f_loudness_from_signal`（時變）與穩態入口，不改 DSP。golden 比較門檻 total 與 specific 皆 `1e-10`。

### D-E. MoSQITo golden 的新角色

`golden_zwtv.rs`／`golden_zwst.rs` 對 total 與 specific 的門檻改為 `5e-3` sone；測試名稱與文件註明「相容性對照」。階段 golden（`golden_core.rs`、`golden_dsp.rs`）不受 slope 變更影響，門檻不變。

---

## Task 1：RED — F-05 與 F-04 的失敗測試

- [x] 新增 `iso532/src/core/calc_slopes.rs` 單元測試 `f05_last_cell_remainder_is_integrated`：取 cross-analysis 報告 §3 的訊號 23 第 3893 幀 NL 向量（21 值，報告附 17 位十進位），期望值為 C（epsilon=0、f64 表、0.24）之 total `4.7653976527…` 的去 epsilon 對應值；用 `sliver_check_024.py` 印出的 `fixed24` 精確值作為期望，容差 1e-12。此測試在修正前必須失敗（現值 4.7517… 差 1.4e-2）。
- [x] 新增 `f04_total_is_not_rounded`：任一非零 NL 幀的 total 乘 1000 不應為整數（在修正前恆為整數，失敗）。
- [x] 新增 `f06_band0_ignores_band20`：`nm = [0; 21]; nm[20] = 1.0` 期望 total 等於 `1.0 * (24.0 - 23.6)` 且 `spec[0..9]` 全為 0（修正前 total 0.982、spec[0] = −9.86，失敗）。
- [x] `cargo test -p iso532 --lib calc_slopes` 三個新測試 RED，其餘 GREEN。

## Task 2：GREEN — 修 `calc_slopes_impl`

- [x] 依 D-B 刪除捨入。
- [x] 依 D-C 處理 `i == 0`。
- [x] 依 D-A 加迴圈後補完；`n_specific` 分支不變。
- [x] `n_only_matches_into_*` 兩個既有測試仍逐位元通過（批次／串流共用的前提）。
- [x] `cargo test -p iso532 --lib`、`cargo clippy -D warnings`、`cargo fmt --check` 全過。

## Task 3：契約與串流不變

- [x] `cargo test -p iso532 --test output_grid --test stream --test stream_scalar --test stream_no_rayon --test simd_parity --test determinism` 全過（不改這些測試）。
- [x] `cargo test -p iso532 --test annexb --test annexb_validator` 全過；若任何 Annex B 點失敗，停止並記錄為 finding，不得調門檻。

## Task 4：C golden 工具與測試

- [x] 新增 `tools/gen_golden_c.py --official <ISO_532-1.c> --header <ISO_532-1.h> --vcvars <vcvars64.bat> --out data/golden-c/`：套用 D-D 單格替換（以 diff 檔進庫）、編譯 wrapper、對 `tools/gen_golden.py` 使用的同九個訊號輸出 total／specific／time 的 little-endian f64 與 `meta.json`（來源 hash、替換版 hash、編譯器、旗標、日期）。`data/` 維持 gitignored；`tools/golden-c.sha256` 進庫。
- [x] 新增 `iso532/tests/golden_c.rs`：zwtv 與 zwst 對 `data/golden-c/` 比較，門檻 `1e-10`，資料缺失時 fail-closed（沿用 `tests/common` 的 Invalid 語意，不得 skip 成 pass）。
  - 實作註記（2026-11-04）：1e-10 只在四個 C-01 尾點成立並強制（`c01_tail_points_match_annex_a_c_within_1e_10`）；全序列 total 差 ≤2.7e-5（官方 C 的 `_ZUP += .0001f` 與 float32 常數）、specific 差 ≤4.4e-2（斜率與核心響度相交格點的 specific 寫法，本階段不改），全序列 1e-10 比對以 `#[ignore]` 保留為已知 finding。
- [x] 記錄四個 C-01 尾端點對未修改 C 的差值（預期 ≤1.3e-7）於 `meta.json` 的 `unmodified_c_delta` 欄，供文件引用。

## Task 5：MoSQITo golden 降級、hash 重凍、版號與文件

- [x] 依 D-E 改 `golden_zwtv.rs`／`golden_zwst.rs` 門檻與說明。
- [x] `tests/hash_gate.rs`：重凍 zwtv／zwst 輸出 hash；commit 訊息列舊新 hash。
- [x] `iso532/Cargo.toml` 與 binding 版本 → 0.4.0；`CHANGELOG.md` 新增 0.4.0 段落（F-04、F-05、F-06、golden 基準變更、F-03 暫定 0.24）。
- [x] README 兩語言：第 281 行基準敘述改寫（D1）；「繼承自 MoSQITo 的相容性選擇」表新增 F-03（暫定 0.24）、F-04、F-05 三列，格式比照 F-01／F-02；`docs/README.md` 索引加決策備忘與 cross-analysis 列。
- [x] `docs/F03-USL12-4-STATUS-2026-10-31.md` 兩語言補「2026-11-03 暫定維持 0.24」一段，不改結論狀態（仍 PENDING）。

## Task 6：收尾

- [x] 全套 `cargo test --workspace`、Python 測試、`cargo bench --no-run`。
- [x] 產出 `docs/RELEASE-0.4.0-<日期>.md` 兩語言草稿（不打 tag；tag 在 Astra 驗收後）。
- [x] 回報：改動檔案清單、hash 舊新值、四個 C-01 尾端點對 C golden 與對未修改 C 的差值、Annex B 結果、串流測試結果。

## 回報格式

完成後回報一份純文字摘要（中文即可）：改動檔案清單；`tests/hash_gate.rs` 舊新 hash；四個 C-01 尾端點（訊號 18／23／24／25）對 C golden 與對未修改 C 的 total 差值；Annex B 測試結果；串流／output_grid 測試結果；Task 1 的 RED 輸出節錄；未完成或改動範圍外的任何事項。不打 tag、不推送；commit 留在本機 `main`，由使用者決定推送時機。

## 驗收條件（交 Astra 前自檢）

1. Task 1 三個測試由 RED 轉 GREEN，且 RED 狀態有紀錄。
2. 四個 C-01 尾端點對 C golden（0.24f 單格替換）total 與 specific 皆 ≤1e-10。
3. 批次＝串流逐位元、output_grid、Annex B 全過。
4. 對未修改官方 C 的差值寫入文件，與決策備忘 §2 的量級一致（尾點 ≤1.3e-7；全序列 ≤3.5e-3 sone）。
5. 不含任何 API、格線、契約變更；diff 只落在 `calc_slopes.rs`、測試、工具、文件、版號。
