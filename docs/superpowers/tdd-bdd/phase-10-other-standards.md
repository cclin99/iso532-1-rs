# Phase 10 TDD/BDD：其他心理聲學標準（workspace 化後擴充）

**對應：** [ROADMAP §1](../../ROADMAP.md)　**狀態：** 🎨 設計（每個新標準各自需 brainstorming → spec → plan）
**規劃測試檔：** 每標準一套 `tests/golden_<standard>.rs` + `tests/annex_<standard>.rs`

> 這不是單一 phase，而是一個**可複製的擴充樣板**：ECMA-418-2、ISO 532-2、sharpness（DIN 45692）、roughness、fluctuation strength 各自套用同一套 golden 驗證方法。本文件定義「新標準要通過哪種測試才算數」的通用契約。

## 1. 測試策略摘要

先做 workspace 化（`dsp-core` / `iso532-1` / `ecma418` …），把已與業務邏輯解耦的 `dsp/`（sosfilt、filtfilt、onepole、SIMD kernel）抽為共用 crate。每個新標準沿用**與 ISO 532-1 完全相同的雙層驗證**：

1. **逐階段 golden parity**：mosqito 同倉庫有 ECMA 與 sharpness 參考實作——用同一套 `gen_golden.py` 模式產生逐階段 `.bin`，Rust 實作逐階段對比。
2. **官方標準合規**：各標準的官方測試訊號/參考值（如 ECMA 附錄、DIN 45692 範例）以 `isoclose` 式容差驗收。
3. **複用既有輸出**：sharpness 直接吃 `LoudnessStationary/TimeVarying` 的 `n_specific`（240 點 specific loudness 已足夠）——測 sharpness 時不重算響度，對既有結構取用。
4. **dsp-core 不回歸**：抽出共用 crate 後，ISO 532-1 的全部 golden 測試必須仍全綠（重構不改行為）。

## 2. BDD 行為情境（Gherkin，通用樣板）

### Feature: workspace 化不改變 ISO 532-1 行為

```gherkin
Scenario: dsp 抽為 dsp-core 後 ISO 532-1 golden 不回歸
  Given dsp/ 抽出為獨立 crate dsp-core
  When 執行 iso532-1 的 golden_dsp / golden_zwst / golden_zwtv / annexb
  Then 全部仍綠（rtol/atol 不變，重構零行為差異）
```

### Feature: 新標準逐階段 golden（以 sharpness 為例）

```gherkin
Scenario: sharpness 對齊 mosqito 參考
  Given 一組訊號經 ISO 532-1 得 n_specific（240 點/bark）
  When 呼叫 sharpness(&n_specific, weighting)
  Then 對 mosqito sharpness golden，rtol<=1e-7, atol<=1e-9

Scenario: sharpness 重用響度輸出而不重算
  Given 既有 LoudnessStationary 結果
  When 計算 sharpness
  Then 直接取 n_specific（不重跑 loudness pipeline）
```

### Feature: 新標準官方合規（以 ECMA-418-2 為例）

```gherkin
Scenario: ECMA-418-2 響度/音調性對齊官方範例
  Given ECMA 附錄的官方測試訊號與參考值
  When 執行 ecma418 響度/tonality
  Then 對參考值 isoclose（各標準規定的容差）
```

## 3. TDD 測試清單（RED→GREEN，每標準複製）

| 測試類別 | 檔案樣板 | 輸入 | 預期 | 容差 |
|---|---|---|---|---|
| dsp-core 抽出回歸 | 既有 golden_* | ISO 532-1 訊號 | 全綠不變 | 沿用 |
| 新標準逐階段 golden | `golden_<std>.rs` | mosqito 逐階段 `.bin` | 逐階段對齊 | 1e-7/1e-9（依標準）|
| 新標準官方合規 | `annex_<std>.rs` | 官方測試訊號 | 參考值 | isoclose（依標準）|
| 重用響度輸出 | `golden_<std>.rs` | `n_specific` | 不重算 loudness | — |

**每個新標準的 RED→GREEN 節奏**：擴 `gen_golden.py` 產該標準逐階段 golden → 寫逐階段失敗測試 → 實作 → GREEN → 再加官方合規測試。

## 4. 已知差異風險 / 排查順序

1. **模組邊界必須乾淨**：workspace 化的前提是 `dsp/` 已與 ISO 532-1 業務邏輯解耦（ROADMAP 已要求）——抽出前先確認無反向依賴（dsp 不 import loudness）。
2. **golden 方法可移植性**：mosqito 同倉庫有 ECMA/sharpness 參考，可沿用 `gen_golden.py` 模式；沒有參考實作的標準（自訂）要另找官方參考資料，缺資料就停下回報（同 Phase 1 鐵律，不造假）。
3. **specific loudness 佈局依賴**：sharpness 依賴 `n_specific` 為 240 點/bark 的既定佈局——若 FFI（phase-6）或串流（phase-7）改過佈局，此處要同步。
4. **容差因標準而異**：各標準的官方容差不同（ISO 5%、有些更嚴）——不可套用 ISO 532-1 的數字，逐標準查其規範。

## 5. 驗收對照（規劃，每標準一輪）

```bash
cargo test -p iso532-1            # workspace 化後 ISO 532-1 不回歸
cargo test -p <new-standard>      # 逐階段 golden + 官方合規
cargo test --workspace           # 全 workspace 綠
```

執行順序：ROADMAP 建議為**最後一項**（workspace 化後逐一加）。每個標準獨立走完整 spec → plan → 實作 → 本樣板測試。
