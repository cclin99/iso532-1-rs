# v0.4.0 效能與標準對照確認

> 對照／Pair: [English](report.en.md) · 來源：zh · 同步 2026-11-05

Claude（Opus 5.5，主代理，非 Astra），2026-11-05 Asia/Taipei。受測：`v0.4.0` = `118322f8300dc752f1d38a79db230a2db5ff2870`（crate 原始碼與 Astra 驗收的 `fca4ccd` 相同）；對照基準：`v0.3.1` = `aa379db8f3dc37f5048ac6c8b7a6d4ba2a6c3b76`。

## 結論

- **效能：0.4.0 沒有造成可量測的端對端退步。** 只有 `calc_slopes` 改了程式；這一段本身慢 6%～12%（含比響度）與 0%～4%（只算總響度）。端對端 Criterion 交錯 A/B 的差異在 −1.9%～+5.4%，跟輪間雜訊（約 ±4%）同一量級；比較一致的訊號是單執行緒批次 +2.0%／+2.2%。經 Python binding 呼叫的 3 秒處理時間，兩版的中位數相同（13.9～14.2 ms）。
- **README 的效能表已過時**，主因是機器狀態而不是 0.4.0：同一台機器上 MoSQITo 也從 6.68 s 變成 7.23 s（+8%）。本次以 2026-11-05 的量測更新 README。
- **標準對照：ISO 532-1 Annex B 的 25 個測試訊號、73,116 個工作簿參考點，0.4.0 與 0.3.1 都 0 個超出逐點容差**，最小餘裕 0.0597 sone/Bark（訊號 2，1.0 Bark）。這是以獨立重寫的判定器重算，結果與 Astra 2026-11-04 那一輪相同。
- **新補的摘要值：** 20 個時變訊號的 Nmax 和 N5（依工作簿公式）全部在 max(0.1, 5%) 範圍內，偏差一致為 +0.14%～+0.18%；0.4.0 跟 0.3.1 的差異 ≤ 7e-4 sone。工作簿本身沒有替 Nmax／N5 訂容差，所以這兩項只算診斷，不是 PASS。
- **合規宣稱的邊界：** 逐點 Annex B 判準可以判 PASS。N5 的正式定義和「恰好 1%」例外規則仍是 UNRESOLVED；`USL[12][4]`（F-03）仍是 PENDING；標準全文未取得。所以**不能宣稱「完整符合 ISO 532-1」**，只能說「通過 Annex B 工作簿的逐點判準」。

## 1. 範圍與方法

- 兩個 tag 各以 `git worktree add --detach` 取出（放在已 gitignore 的 `tmp/`），各用獨立的 `CARGO_TARGET_DIR`。主工作樹與專案 `.venv` 都沒有修改。
- Python 量測用兩個全新 venv，各裝一版 wheel（`--no-deps --no-index`）；numpy、mosqito、pytest、openpyxl 透過 `.pth` 借用 `.venv`。
- Annex B 輸入用 Astra 2026-11-04 那一輪解碼並校準過的 `sig1..25.bin`，SHA-256 已跟該輪的 `contracts-results.json` 核對過。
- 環境：AMD Ryzen 5 3600（12 logical processors）、64 GB、Windows 10 Pro 19045、電源計畫 Balanced；rustc 1.99.1、Criterion 0.5.1、rayon 1.12.0、Python 3.11.9、NumPy 2.4.6、MoSQITo 1.2.1。詳見 [environment.json](environment.json)。

## 2. 發行產出物（自 `v0.4.0` 建置）

| 檔案 | SHA-256 |
|---|---|
| `iso532-0.4.0-cp39-abi3-win_amd64.whl` | `724b272c86ee35b27a51852674538adeeb1979143364de89c59b5476ad244cc0` |
| `iso532_ffi.dll` | `11a126257863df923e8ae41108fddb570f3f30a2bee0ed3be8c73b688d4ceb28` |
| `iso532_ffi.dll.lib` | `e5b7a8f812cd9e6d8be7a22f15dd0493ef3ebda7920757f3858d1e63026c05a9` |
| `iso532.h` | `0f548fd348cb0e3999ce8892bec05d4a5afd53740eb695428ad0eca9a45b709b` |

- `cargo build --locked --release -p iso532-ffi`；`maturin build --release --locked`（maturin 1.14.1）。
- `iso532.h` 取自 tag 的 Git blob 原樣，跟 0.3.1 發布的 header 位元相同；import library 也跟 0.3.1 位元相同（匯出符號未變）。worktree 取出的 header 因 autocrlf 是 CRLF，所以不採用。
- wheel 的 METADATA 是 `Version: 0.4.0`；在全新 venv 中以 `ISO532_REQUIRE_PARITY=1` 跑 `iso532-py/tests`：87 passed（[pytest-wheel-v0.4.0.log](pytest-wheel-v0.4.0.log)）。
- DLL 和 wheel 內嵌建置資訊，換一台機器重建不會得到相同 hash。防毒掃描（建置機為 Avira）尚未執行，需手動完成。產出物沒有上傳。

## 3. 效能

### 3.1 `calc_slopes` 階段

[slopes_harness.rs.txt](slopes_harness.rs.txt) 以 path 依賴分別編譯兩版，用 Annex B 訊號 2–25 產生 274,860 個 21 頻帶核心響度向量，各重複 30 次，交錯跑 3 輪（[slopes-stage.log](slopes-stage.log)）。輸入取自 main loudness（尚未經 nonlinear decay），所以 F-05 分支的觸發頻率跟完整 pipeline 不完全相同。

| 每個向量（ns，三輪中位數） | v0.3.1 | v0.4.0 | 變化 |
|---|---:|---:|---:|
| `calc_slopes`（含 240 格比響度，批次用） | 4614／4743／4719 | 4873／5129／5277 | +5.6%～+11.8% |
| `calc_slopes_n_only`（只算總響度，串流用） | 4503／4593／4582 | 4508／4715／4779 | +0.1%～+4.3% |

兩版的 checksum 不同，三輪之間各自一致。

### 3.2 Criterion 端對端（10 秒、480,000 samples、5,000 個輸出 frame）

[criterion/run_criterion.sh](criterion/run_criterion.sh) 交錯跑 3 輪，每輪依序跑 v0.3.1、v0.4.0；數值是 Criterion 點估計的三輪中位數（[criterion/criterion-summary.json](criterion/criterion-summary.json)）。

| 工作量 | v0.3.1 (ms) | v0.4.0 (ms) | 變化 | 三輪範圍 v0.3.1／v0.4.0 |
|---|---:|---:|---:|---|
| ZWTV batch，12 threads，scalar | 63.187 | 66.577 | +5.4% | 62.9–66.8／63.6–67.3 |
| ZWTV batch，12 threads，AVX2 | 49.155 | 48.898 | −0.5% | 46.2–50.6／48.5–49.6 |
| ZWTV batch，1 thread，scalar | 351.350 | 358.990 | +2.2% | 351.2–355.1／352.3–361.8 |
| ZWTV batch，1 thread，AVX2 | 248.890 | 253.880 | +2.0% | 248.3–259.2／251.2–266.7 |
| stream 480-sample chunks，scalar（`RAYON_NUM_THREADS=1`） | 340.820 | 334.320 | −1.9% | 326.4–347.8／331.3–350.2 |
| stream 480-sample chunks，AVX2（`RAYON_NUM_THREADS=1`） | 228.080 | 239.690 | +5.1% | 223.7–233.4／231.0–242.3 |
| stream，scalar（預設 threads） | 320.650 | 333.960 | +4.2% | 320.6–346.9／330.9–344.2 |
| stream，AVX2（預設 threads） | 232.920 | 233.850 | +0.4% | 225.2–236.6／226.1–238.8 |
| filter bank，12 threads，scalar | 15.348 | 15.329 | −0.1% | — |
| filter bank，12 threads，AVX2 | 5.610 | 5.572 | −0.7% | — |

判讀：串流本身是單執行緒，兩種 thread 設定其實是同一個工作量，結果卻分別是 +5.1% 和 +0.4%，可見 ±5% 以內多半是雜訊。filter bank 沒有改程式，差異在 ±1% 以內，可當作對照組。單執行緒批次兩個 backend 都是 +2%，跟 3.1 節的 slopes 變慢一致：批次每 4 個內部 frame（2 kHz）呼叫 1 次 `calc_slopes_into`、3 次 `calc_slopes_n_only`（`iso532/src/zwtv/mod.rs:129-134`），10 秒輸入約 5,000 次加 15,000 次；用 3.1 節的增量推算約 +3 ms（+1.3%），跟實測的 +5 ms（+2%）同一量級。串流只呼叫 `n_only`，推算約 +2 ms（+1%），落在雜訊內。

### 3.3 Python binding 與 MoSQITo（3 秒訊號）

- `tools/compare_mosqito.py`（0.4.0 wheel，30 次）：ISO532 binding 平均 14.963 ms（SD 1.262），MoSQITo 7.233612 s（SD 0.186382），相對速度 483.44 倍。差異值與 README 相同：預設 `nl_init="zero"` 時 `N(t)` 5.81e-3 sone、`N_specific(t)` 3.25e-2 sone/Bark（F-02 起始段）。見 [compare-mosqito-v0.4.0.log](compare-mosqito-v0.4.0.log)。
- binding 交錯 A/B（[binding_ab.py](binding_ab.py)，3 輪 × 30 次）：平均 v0.3.1 13.99／14.78／14.14 ms，v0.4.0 14.02／14.28／15.03 ms；中位數 13.90／14.41／14.16 對 13.90／14.08／13.95 ms。看不出差異。

### 3.4 與 README 2026-07 基線比較

| 項目 | README 基線 | 2026-11-05（v0.4.0） |
|---|---:|---:|
| ZWTV batch 12 threads scalar／AVX2（2026-07-10） | 142.224／47.461 ms | 66.577／48.898 ms |
| ZWTV batch 1 thread scalar／AVX2（2026-07-21，`8fde6b6`） | 351.460／275.410 ms | 358.990／253.880 ms |
| stream scalar／AVX2（2026-07-21） | 360.930／233.420 ms | 334.320／239.690 ms |
| 3 秒 binding／MoSQITo（2026-07-20） | 12.449 ms／6.681 s | 14.963 ms／7.234 s |

12 threads scalar 的大幅縮短來自 7 月之後的其他改動，不是 0.4.0。MoSQITo 跟 binding 同樣變慢約 8%～20%，而 binding 的版本 A/B 沒有差異，所以 3 秒那一列的變化是機器狀態造成的。

## 4. 標準對照（ISO 532-1:2017 Annex B）

### 4.1 逐點判準

判準為 `|got − ref| ≤ max(0.1, 0.05·|ref|)`，取自官方 Annex B 工作簿（V-01）。穩態訊號比對總響度與 240 格比響度；時變訊號比對工作簿每個時間點的 N(t)，訊號 6–13 另外比對工作簿指定的那條 Bark 的 N′(t)。訊號 15 是 diffuse field，其餘是 free field。腳本：[compliance.py](compliance.py)。

| 工作簿 | 訊號 | 參考點 | 超出 | 最小餘裕（位置） |
|---|---|---:|---:|---|
| B.2 穩態（1/3 倍頻程位準輸入） | 1 | 241 | 0 | 0.0999（N′，index 226） |
| B.3 穩態合成訊號 | 2–5 | 964 | 0 | 0.0597（訊號 2，N′ 1.0 Bark） |
| B.4 時變合成訊號 | 6–13 | 46,400 | 0 | 0.0952（訊號 9，N(t)） |
| B.5 時變技術訊號 | 14–25 | 25,511 | 0 | 0.0954（訊號 17，N(t)） |
| 合計 | 1–25 | 73,116 | 0 | 0.0597 |

v0.3.1 的結果完全相同。訊號 2–25 用 wheel 重算的輸出跟 Astra 的 Rust 輸出逐位元相同（兩版皆是）；訊號 1 沒有 Python 入口，沿用 Astra 的 Rust 輸出，並核對其 hash。

### 4.2 Nmax 與 N5（診斷）

工作簿 B5 列出 Nmax，B6 以 `PERCENTILE(…, 0.95)` 計算 N5，但沒有替這兩個值訂容差。我依工作簿公式的列範圍，從我們的 N(t) 算出相同統計量，再以 max(0.1, 5%) 作為診斷尺度。工作簿快取的 N5 跟我依公式重算的值 20／20 相符，Nmax 也都等於參考 N 欄的最大值。

- Nmax：20 個訊號全部在尺度內，偏差 +0.140%～+0.170%，最大絕對差 +0.054 sone（訊號 16，參考值 38.536），最小餘裕 0.208（訊號 10）。
- N5（工作簿定義）：全部在尺度內，偏差 +0.139%～+0.176%，最小餘裕 0.099（訊號 10）。
- 訊號 12、13 的 N5 公式引用的是 E 欄（5% 容差的下界），不是 N 欄；這裡照工作簿公式，對我們的 N 套用同樣的轉換後再比。這是先前報告（`docs/修正報告2.md` §11.6）已指出的公式語義疑點，維持原樣記錄。
- 改用官方 CLI 的 N5 定義（整段輸出、取排序後第 ⌊0.95n⌋ 個與前一個的平均）時，跟工作簿值最多差 0.416 sone（訊號 12）。這是兩種定義本身的差別，不是引擎誤差。
- 0.4.0 對 0.3.1：Nmax 最多差 7.0e-4 sone（訊號 14），N5 最多差 6.8e-4 sone（訊號 20）。

所有時變訊號的 Nmax 與 N5 都一致偏高約 0.15%，跟逐點比對的趨勢相同；這遠在容差內，但值得在之後追查來源（例如濾波器或校準）時一併記錄。

### 4.3 合規狀態

| 項目 | 狀態 | 依據 |
|---|---|---|
| Annex B 逐點判準，25 個訊號 | **PASS**（0／73,116） | 4.1；與 Astra 2026-11-04 相同 |
| Nmax、N5 摘要值 | 診斷：全部在 max(0.1, 5%) 內 | 4.2；工作簿未訂容差 |
| N5 正式定義 | UNRESOLVED | 工作簿、CLI 定義不同；訊號 12／13 公式引用 E 欄；`docs/修正報告2.md` §11.6、§15.5 |
| 「恰好 1%」例外規則 | UNRESOLVED，目前不適用 | 沒有任何點超出，所以不需要用到例外 |
| 對 Annex A 官方 C 程式（`USL[12][4]` = 0.24f） | PASS（0.4.0 驗收門檻） | 尾點 9.0e-11、全序列 2.7e-5／2.1e-4；Astra 2026-11-04 |
| `USL[12][4]`（Table A.9，F-03） | PENDING | 2017-11 更正版確實改了 Table A.9，但改哪一格未知；`docs/F03-USL12-4-STATUS-2026-10-31.md` |
| 穩態前端 | 刻意採 MoSQITo 相容的頻譜路徑，待決 | 訊號 3／5 偏差 +0.82%／−0.76%，在容差內 |
| 標準全文 | 未取得 | 逐點判準取自工作簿，不是逐條核對條文 |

## 5. 限制

- 單一台機器、單次 session 的量測；交錯排程可以抵消緩慢漂移，但無法排除背景程式的瞬間干擾。
- 階段 harness 的輸入是 nonlinear decay 之前的核心響度。
- 沒有在 Linux 上量測效能；產出物只建置 Windows x64。
- 合規部分重用了 Astra 解碼後的輸入，沒有重新從 WAV 解碼；輸入 hash 已核對。

## 6. 證據檔案

| 檔案 | 內容 |
|---|---|
| [environment.json](environment.json) | 受測 commit、主機、工具鏈、wheel hash |
| [artifacts-SHA256SUMS.txt](artifacts-SHA256SUMS.txt) | 四個產出物的 SHA-256 |
| [pytest-wheel-v0.4.0.log](pytest-wheel-v0.4.0.log) | 0.4.0 wheel 的 Python 測試 |
| [slopes_harness.rs.txt](slopes_harness.rs.txt)、[slopes-stage.log](slopes-stage.log) | `calc_slopes` 階段量測 |
| [criterion/](criterion/) | 執行腳本、彙總腳本、12 份 Criterion log、彙總 JSON |
| [binding_ab.py](binding_ab.py)、[binding-ab.log](binding-ab.log) | binding 交錯 A/B |
| [compare-mosqito-v0.4.0.log](compare-mosqito-v0.4.0.log) | README 的 3 秒 MoSQITo 比對 |
| [compliance.py](compliance.py)、[compliance-v0.4.0.json](compliance-v0.4.0.json)、[compliance-v0.3.1.json](compliance-v0.3.1.json) | Annex B 逐點、Nmax／N5、交叉核對 |
| [delivery-integrity.json](delivery-integrity.json) | 去識別化後各檔 SHA-256（排除自身） |

建置產物、WAV、wheel、DLL 與 worktree 都留在 `tmp/`，不進庫。
