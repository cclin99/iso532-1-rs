# slope 階段對齊 Annex A：C-01 尾值根因與 F-03 係數的決策

> 對照／Pair: [English](C01-F03-SLOPE-ALIGNMENT-DECISION-2026-11-03.md) · 來源：zh · 同步 2026-11-03

2026-11-03（Asia/Taipei）。程式快照 `aa379db`（v0.3.1）。決策備忘，不改程式、不改 golden。證據：Astra 的 [`verification/2026-11-03-C01-zero-pad-aa379db/`](verification/2026-11-03-C01-zero-pad-aa379db/)、[`verification/2026-11-03-C01-tail-root-cause-aa379db/`](verification/2026-11-03-C01-tail-root-cause-aa379db/)、[`verification/2026-11-03-F03-coefficient-hypothesis-aa379db/`](verification/2026-11-03-F03-coefficient-hypothesis-aa379db/)，以及 Claude 的交叉分析 [`verification/2026-11-03-C01-cross-analysis-aa379db/`](verification/2026-11-03-C01-cross-analysis-aa379db/)。

## 0. 一句話結論

Rust 與官方 Annex A C 程式在相同輸入下的全部差異已追到四個來源，其中三個是從 MoSQITo 1.2.1 逐位元繼承的偏差。決定：正確性參考改為 Annex A；修正每幀捨入（F-04）與最後格點平台段遺漏（F-05）；`USL[12][4]` 暫定維持 0.24；golden 改以官方 C 產生、門檻 1e-10；版本 0.4.0。

## 1. 背景

C-01 的四個尾端點（Annex B 訊號 18／23／24／25）沒有官方對照值。Astra 以補零輸入的官方 C 建立對照後，specific 960 值全部 ≤1e-14，但四個 total 差 2.0e-7 ～ 4.2e-7 sone，嚴格 gate 未過（PARTIAL）。Astra 第二輪以固定順序的階段替換把尾差分解：去掉 Rust 的每幀捨入解釋 67–98%，剩餘歸入 slope 階段與 main 階段，未再隔離。Claude 的交叉分析獨立重現 Astra 全部數字（自寫 TW 到 1 ulp），並把兩處未解殘差閉合。

## 2. 差異來源（相同輸入、相同上游歷史）

| # | 來源 | 來自 | 對尾點 | 對全序列加權輸出（四訊號） | 證據 |
|---|---|---|---|---|---|
| F-04 | 每幀 total 捨入到 0.001（N≤16）或 0.01 sone，`calc_slopes.rs:161-165`；C 無 | MoSQITo `_calc_slopes.py:350-352` | 主因 67–98%；機制是衰減段 raw N < 0.0005 被捨成 0，70 ms 慢支路把虧損帶到尾點 | ≤1.0e-3 sone | tail-root-cause T1；cross-analysis 時間線 |
| F-03 | `USL[12][4]`：Rust／MoSQITo／SQAT 0.24，C 0.22；表格唯一差格 | 來源待裁定 | 1e-8 量級；訊號 25 為 0 | **≤3.5e-3 sone，全序列主因** | tail-root-cause cell 反事實；cross-analysis 逐格比對 |
| F-05 | 斜率段在 band 最後一個 0.1 Bark 格點啟動且在 ZUP 前碰到核心響度時，到 ZUP 的平台段從未加入，改由下一 band 回填 | MoSQITo 向量化演算法，Rust 逐位元相同 | 6e-10 ～ 8e-9（Astra 的 unresolved 殘差） | ≤1.4e-3 sone；每訊號約 1% 幀，單幀 1e-3 ～ 2.6e-2 sone | cross-analysis `sliver_check.py`：四訊號 40／63／38／31 個稀疏幀全部命中、無誤判；補上後逐幀 ≤1.4e-14、尾點 ≤2e-17 |
| C-f32 | C 程式自身的 float32 常數：`_ZUP += .0001f`、ZUP／RNS／USL 表、main 的 `.0635f`／`0.4f`／`0.32f`／A0／DCB | 官方 C | ~1e-11 | 單幀 ≤7e-8 | cross-analysis `dense_check.py`、`main_check.py`（main 階段閉合到 ≤4.4e-16） |

另一項順帶發現：公開匯出的 `core::calc_slopes` 若收到 nm[20] > nm[0] 的輸入，band 0 會從 band 20 繞回（`prev_grid_index(0) = 239`），產生負 specific loudness 並灌水 total。經 pipeline 不可達（C 與 Rust 的 main loudness 都固定 nm[20] = 0，端到端 12.5 kHz 純音與 >8 kHz 噪音測試差 ≤4e-4），屬 API 穩健性風險，列為 F-06 加固項。

## 3. 決定

**D1. 正確性參考 = ISO 532-1:2017 Annex A C 程式。** MoSQITo 自己也引用 Annex A；兩者分歧時 MoSQITo 無仲裁地位。README 第 281 行「MoSQITo 1.2.1 是主要的獨立實作基準」改寫為「Annex A 為正確性參考；MoSQITo 為相容性與診斷基準」。F-01、F-02 已是同一原則的先例。

**D2. 修 F-04 與 F-05，改在 `calc_slopes_impl` 本體。** 兩者與係數選擇彼此獨立（0.24 下同樣閉合到算術雜訊）。串流與批次呼叫同一函式，會一起改；保留 n_only 對 into 的逐位元測試。

**D3. `USL[12][4]` 暫定維持 0.24。** 依 SQAT 與 MoSQITo 的參數基準；Astra F-03 報告已證明現有資料無法判定 0.22 或 0.24，ISO Table A.9 原文該格仍 PENDING。日後若原文證實 0.22，改一格是另一次數值變更，需再出 minor 版並重生 golden。

**D4. golden 改以官方 C 產生。** 參考程式為官方 C 只替換 `USL[12][4]` 一格 0.22f→0.24f 的診斷版本，原檔與替換版 hash 都列出；門檻 1e-10 sone（高於 C 的 float32 殘留 3～6e-11、低於三項缺陷）。同時保留對未修改 C 的差值記錄（四訊號尾點 1e-8 ～ 1e-7，全序列 ≤3.5e-3 sone）。MoSQITo golden 降為容差對照（≤5e-3 sone），不再當驗收。

**D5. 版本 0.4.0。** 數值變更；重凍 zwtv／zwst hash；Annex B 符合性測試預期不變；批次＝串流 gate 維持。

## 4. 不變的部分

- API、輸出格線契約（C-01 ceil 決定）、串流契約、SIMD 分派、C ABI、Python shape 均不變。
- Annex B 容差（5% 或 0.1 sone）本來就看不出這三項，符合性判定不變。
- MoSQITo 仍是架構與 API 的來源、效能對照、穩態前端的合法選擇，以及相容模式（F-02 的 `NlInit::MosqitoTail` 模式）。

## 5. 風險與未決

- Table A.9 原文仍未取得；D3 是暫定。
- C golden 的產生需要本機保存的官方 C 與 MSVC，git 裡沒有；工具要像 `tools/gen_golden.py` 一樣接受外部素材並記錄 hash。
- F-05 修正後 Rust 與 C（epsilon=0、f64 表）逐幀差 ≤1.4e-14，但對未修改 C 仍有 C-f32 的 ~1e-11；不仿造 float32 升位，這是 D4 門檻的理由。

## 6. 執行

phase 計畫：[`superpowers/plans/phases/phase-0.4.0-slope-annexa.md`](superpowers/plans/phases/phase-0.4.0-slope-annexa.md)，交實作者（Claude Opus 5.5）；完成後由 Astra 獨立驗收。
