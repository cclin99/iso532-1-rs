# C-01 尾值差異交叉分析（Claude，對 Astra 兩輪交付的獨立重現與殘差閉合）

> 對照／Pair: [English](report.en.md) · 來源：zh · 同步 2026-11-03

- 日期：2026-11-03（Asia/Taipei）
- 受驗快照：`aa379db`（v0.3.1）
- 執行者：Claude（主代理），非 Astra
- 性質：對 [`2026-11-03-C01-zero-pad-aa379db/`](../2026-11-03-C01-zero-pad-aa379db/) 與 [`2026-11-03-C01-tail-root-cause-aa379db/`](../2026-11-03-C01-tail-root-cause-aa379db/) 的交叉驗證；純診斷，不改程式、測試、golden。
- 結論用途：[`docs/C01-F03-SLOPE-ALIGNMENT-DECISION-2026-11-03.zh-TW.md`](../../C01-F03-SLOPE-ALIGNMENT-DECISION-2026-11-03.zh-TW.md)

## 1. 問題與結論

**問題。** Astra 第二輪把四個尾點（Annex B 訊號 18／23／24／25）的 Rust 對官方 C 差值分解後，仍有兩處「未隔離」殘差：去捨入後 slope 階段剩 1.2e-9 ～ 8.5e-9，main 階段剩 ~1e-11。本輪要回答：(a) Astra 的數字能否獨立重現；(b) 兩處殘差的機制是什麼；(c) 差異在整段訊號上有多大；(d) 這些差異是否從 MoSQITo 繼承。

**結論。**

1. Astra 的尾點數字可重現：用自寫的 temporal weighting 對 Astra 留下的階段陣列重算，與 Astra 的 12 個尾值 7 個逐位元相同、其餘 ≤6 ulp（≤2.2e-18，[`logs/repro_check.log`](logs/repro_check.log)）；slope 階段的 Rust 與 C 皆以 Python 逐位元移植通過驗證（訊號 18 全部 4340 幀、訊號 23 抽樣 1703 幀，0 個 mismatch）。Astra 的驗證合理。
2. slope 殘差 = 一項演算法缺陷（F-05，「最後格點平台段遺漏」）加上 C 程式自身的 float32 常數。把遺漏的平台段依 Annex A 補回後，Rust 移植對 C 移植（epsilon = 0、f64 表）逐幀 ≤1.4e-14，尾點 ≤2e-17。
3. main 殘差 = C 的 float32 常數（`.0635f`、`0.4f`、`0.32f`、A0／DCB 表）。以同樣升位的移植對 C 核心響度逐幀 ≤4.4e-16。
4. 三項偏差（每幀捨入 F-04、`USL[12][4]` F-03、F-05）都是 MoSQITo 1.2.1 的行為，Rust 逐位元繼承；MoSQITo 對三個稀疏幀的輸出與 Rust 捨入值逐位元相同。
5. 整段訊號上，對 C 的加權輸出差最大 3.5e-3 sone，F-03 佔主導；尾點上 F-04 佔主導。
6. 公開的 `core::calc_slopes` 在 nm[20] > nm[0] 時 band 0 會從 band 20 繞回，產生負 specific loudness；經 pipeline 不可達（main loudness 固定 nm[20] = 0），列為 API 加固項 F-06。

## 2. 輸入與工具

全部輸入來自 Astra 第二輪留在 `tmp/c01-tail-root-cause-aa379db-run2/` 的材料（未進 git），hash 列於 [`inputs.sha256.txt`](inputs.sha256.txt)：

- 官方 `ISO_532-1.c`（SHA-256 `a74b45ed…834491`，與 Astra 記錄一致）與 Astra 的階段 wrapper `stages.c`／`stages.dll`（`rc_slopes`、`rc_public`）。
- Astra 的 Rust 探針 `c01-root-probe.exe`（模式 `public`，未修改的 crate 快照）。
- 每訊號的階段陣列：`R-pipeline/{tol,core,nl,slope_raw,slope_raw22,slope_round}.bin`、`C-core-on-Rtol.bin`、`C-slope-on-Rnl-total.bin`。
- MoSQITo 1.2.1（`.venv`）的 `_calc_slopes`。
- 本資料夾的腳本以 `C01_WORK` 指向該目錄執行；日誌在 [`logs/`](logs/)。Python 3.11.9、NumPy 2.4.6。

## 3. 方法與結果

### 3.1 逐位元移植（`slope_trace.py`）

- `c_slopes`：官方 `f_calc_slopes`（第 839–937 行）的 Python 移植，表格以 float32 升位、`_ZUP += 0.0001f`。
- `rust_slopes`：`calc_slopes_impl` 去掉第 161–165 行捨入的移植，含 `r8`、`get_rns_index` 的兩種比較與 band-0 繞回。
- 驗證（[`logs/slope_trace.log`](logs/slope_trace.log)）：C 移植對 `C-slope-on-Rnl-total.bin`、Rust 移植（0.24 與 0.22 表）對 `slope_raw.bin`／`slope_raw22.bin`，訊號 18 全 4340 幀、訊號 23 每 3 幀共 1703 幀，皆 0 個 mismatch。

### 3.2 slope 殘差的兩個成分（`dense_check.py`）

對訊號 18 前 4333 幀，`raw22 − C 變體` 的幀數分布（[`logs/dense_check.log`](logs/dense_check.log)）：

| C 變體 | >1e-12 | >1e-10 | >1e-6 | >1e-4 |
|---|---|---|---|---|
| 原版（epsilon、float32 表） | 3382 | 3244 | 887 | 38 |
| epsilon = 0 | 3382 | 3243 | 40 | 38 |
| epsilon = 0 且 f64 表 | 40 | 40 | 40 | 38 |

把 C 自身的升位移除後，差異只剩 40 個「稀疏幀」（訊號 23／24／25 各 63／38／31），其餘 2949 幀差 ≤1e-13。即稠密的小差來自 C 的 float32 常數，稀疏的大差另有機制。

### 3.3 稀疏幀的機制 = F-05（`slope_trace.py trace`、`sliver_check.py`）

訊號 23 第 3893 幀（[`logs/slope_trace.log`](logs/slope_trace.log)）：band 3 的斜率段在最後一個格點（j = 34）啟動，於 Z = 3.438 碰到核心響度 0.0995，C 隨即補平台段到 ZUP 3.5；Rust 的格點迴圈已無下一格可處理，平台段 3.438 → 3.5 從未加入，band 4 從 3.438 起算（回填），淨差 +1.38e-2 sone。第 4017、3981 幀同型（band 19／18）。

`rust_slopes_fixed` 在格點迴圈後依 Annex A 補完該段（[`logs/sliver_check.log`](logs/sliver_check.log)）：

| 訊號 | 稀疏幀 | 其中補完觸發 | 非稀疏幀誤觸發 | 補完後逐幀 max\|Rust−C(eps0,f64)\| | 尾點 fixed−C(eps0,f64) | 尾點 fixed−C 官方 |
|---|---|---|---|---|---|---|
| 18 | 40 | 40 | 0 | 1.42e-14 | −5.2e-18 | −3.46e-11 |
| 23 | 63 | 63 | 0 | 1.07e-14 | −1.8e-17 | +6.06e-11 |
| 24 | 38 | 38 | 0 | 8.88e-15 | −1.1e-17 | −5.44e-11 |
| 25 | 31 | 31 | 1（良性，差 ≤1e-13） | 8.88e-15 | −6.3e-18 | −3.47e-11 |

對 C 官方的 3～6e-11 完全等於 C(eps0,f64) 對 C 官方的差，即 C 自身的 float32 常數。

### 3.4 係數 0.24 下同樣閉合（`sliver_check_024.py`）

兩側皆用 0.24（[`logs/sliver_check_024.log`](logs/sliver_check_024.log)）：逐幀 ≤1.42e-14；尾點對「官方算術、只換一格 0.24f」的 C 為 −3.46e-11／+6.05e-11／−5.44e-11／−3.47e-11；對未修改 C（0.22）為 −1.43e-8／−1.28e-7／−9.30e-9／−3.47e-11；全序列加權最大差 2.97e-3／1.53e-3／3.53e-3／5.56e-7 sone。F-04、F-05 的修正與係數選擇獨立。

### 3.5 main 殘差（`main_check.py`）

[`logs/main_check.log`](logs/main_check.log)：f64 移植對 Rust 核心響度逐位元相同（0 mismatch）；C 風格移植（`.0635f`、`0.4f`／`0.32f`、A0／DCB f32）對 C 核心響度 max ≤4.4e-16（四訊號 127／166／145／131 個 1-ulp 幀）。單項：A0／DCB f32 貢獻 6.5e-8／幀，`.0635f` 8e-9／幀。main 殘差完全是 C 的 float32 常數。

### 3.6 band-0 繞回（`ctypes_check.py`、`band0_real-main.rs.txt`、`e2e_band0.py`）

[`logs/e2e_band0_ctypes.log`](logs/e2e_band0_ctypes.log)、[`logs/band0_real.log`](logs/band0_real.log)：合成幀 nm[0] = 0、nm[20] = 1 時，官方 C total 0.400、Rust 真實 crate total 0.982 且 spec[0] = −9.8575。但四訊號的 NL 歷史中 nm[20] > 0 的幀為 0（`band0scan`），端到端 12.5 kHz 純音、>8 kHz 噪音、白噪音、1 kHz 純音的 Rust 對 C 差 ≤1.8e-3 sone、specific 最小值皆 0。繞回只在直接呼叫公開 `calc_slopes` 時可達。

註：`band0_real.log` 由 scratch 專案產生，其 `main.rs` 比本資料夾存檔的版本多一行重複的 `only nm20=1.0 spec check` 案例，數值與第三案相同。

### 3.7 MoSQITo 繼承

同一日誌：MoSQITo `_calc_slopes` 對訊號 23 第 3893／4017／3981 幀的 total 與 Rust 捨入值逐位元相同（4.765／13.309／7.649），官方 C 為 4.7516／13.3136／7.6544。

## 4. 對 Astra 驗證的判斷

- 預註冊設計、逐位元基線／重放控制、固定順序替換與反向控制均適當；尾點數字獨立重現（`repro_check.py`：baseline、remove_R_rounding、replace_slopes_C 三步 × 四訊號，worst 2.2e-18）。
- 「去捨入後仍不達 1e-14」的 gate 結果正確，其殘差本輪已歸因，不是 Astra 的方法缺陷，而是實驗範圍止於階段層級。
- Astra 未把 F-05 當作缺陷命名，因為其稀疏幀對尾點的貢獻只有 1e-9 量級；本輪以逐幀比較才看到 1e-2 sone 的單幀差。

## 5. 交付清單

| 檔案 | 內容 |
|---|---|
| `report.md`／`report.en.md` | 本報告 |
| `repro_check.py` | 以自寫 TW 重現 Astra 的 12 個尾值 |
| `slope_trace.py` | 逐位元移植、驗證、追蹤、band-0 測試 |
| `dense_check.py` | C 變體分離稠密／稀疏差 |
| `sliver_check.py`／`sliver_check_024.py` | F-05 補完與閉合（0.22／0.24） |
| `main_check.py` | main 階段 float32 常數閉合 |
| `e2e_band0.py`、`ctypes_check.py`、`band0_real-*.txt` | band-0 端到端與直接呼叫 |
| `logs/*.log` | 本次重跑輸出 |
| `inputs.sha256.txt` | 外部輸入 hash |
| `delivery-check.md`、`delivery-integrity.json` | 去識別化與完整性 |
