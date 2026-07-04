# Phase 4 TDD/BDD：AVX2 加速（dispatch + kernels）

**對應計畫：** [plans/phases/phase-4-avx2.md](../plans/phases/phase-4-avx2.md)（主計畫 Task 13–15）　**狀態：** ✅ 已實作
**測試檔：** `tests/simd_parity.rs`（新建）、`src/simd/mod.rs`（`#[cfg(test)]`）

## 1. 測試策略摘要

AVX2 kernel 是既有 scalar 的**加速改寫，非新行為**——因此驗證核心是 **parity（AVX2 輸出 == scalar 輸出）**，而非再對 mosqito golden 一次：

1. **runtime dispatch 不 panic**：`avx2_available()` / `set_force_scalar` / `use_avx2()` 在任何機器上安全（非 x86_64 編譯期回 false）。
2. **AVX2 vs scalar parity**：對 deterministic 輸入，`third_octave_levels_avx2` 對 `_scalar`（`1e-10/1e-12`）、`nl_loudness_avx2` 對 `_scalar`（`1e-12/1e-14`）。FMA 改變捨入，只容許極小漂移。
3. **golden 雙路徑重跑**：AVX2 就緒後，Phase 2/3 的 golden 測試在支援 AVX2 的機器上會走 AVX 路徑 = **對 mosqito 的第二次獨立驗證**。

> ⚠️ **skip ≠ pass**：parity 測試在無 AVX2+FMA 的機器上會 `return`（skip）。在這種機器上 `cargo test` 全綠**只證明 scalar 正確**，不代表驗過 SIMD。宣告本 phase 完成必須在 AVX2+FMA 機器上實跑。

## 2. BDD 行為情境（Gherkin）

### Feature: SIMD runtime dispatch（simd/mod.rs）

```gherkin
Scenario: 特徵偵測不 panic 且可強制 scalar
  When 呼叫 avx2_available()
  Then 不 panic（非 x86_64 回 false）
  When set_force_scalar(true)
  Then use_avx2() == false
  And set_force_scalar(false) 還原
```

### Feature: AVX2 濾波器組 kernel（third_octave_levels_avx2）

```gherkin
Scenario: 28 頻帶 = 7×f64x4 的 AVX2 濾波對齊 scalar
  Given 一段 deterministic 偽隨機 1 秒訊號（LCG，固定種子）
  And 執行機器支援 AVX2+FMA
  When 分別呼叫 third_octave_levels_scalar 與 third_octave_levels_avx2
  Then 兩者逐元素 rtol<=1e-10, atol<=1e-12

Scenario: 無 AVX2 機器誠實 skip
  Given avx2_available() == false
  When 執行 filter_bank_avx2_matches_scalar
  Then 印出提示並 return（不誤判為 pass）
```

### Feature: AVX2 非線性衰減 kernel（nl_loudness_avx2）

```gherkin
Scenario: 21 頻帶 = 6×f64x4（3 lane padding）分支改 compare+blend 對齊 scalar
  Given 合成 core loudness（21 帶 × 500 frame，含攻擊與衰減）
  And 執行機器支援 AVX2+FMA
  When 分別呼叫 nl_loudness_scalar 與 nl_loudness_avx2
  Then 兩者逐元素 rtol<=1e-12, atol<=1e-14

Scenario: blend 決策與 scalar 分支逐一對應
  Given nl_lp_step 的 decay/attack 分支語意（Phase 3 最終版）
  When AVX kernel 用 max/min/blendv 表達同一決策
  Then 對所有 lane 的選擇與 scalar 完全一致（parity 容差內）
```

### Feature: golden 雙路徑（回歸）

```gherkin
Scenario: AVX2 路徑下 golden 仍對齊 mosqito
  Given AVX2+FMA 可用且未 force_scalar
  When 執行 cargo test --test golden_zwtv
  Then third_octave_levels / nl_loudness 走 AVX 路徑仍全過（雙重驗證）
```

## 3. TDD 測試清單（RED→GREEN）

| 測試名 | 檔案 | 輸入 | 預期 | 容差 (rtol/atol) | 對應 Task |
|---|---|---|---|---|---|
| `detection_does_not_panic` | src/simd/mod.rs | — | `use_avx2()` 隨 force flag 切換 | 布林精確 | 13 |
| `filter_bank_avx2_matches_scalar` | simd_parity | LCG 48000 樣本 | avx2 == scalar | 1e-10 / 1e-12 | 14 |
| `nl_loudness_avx2_matches_scalar` | simd_parity | 合成 21×500 core | avx2 == scalar | 1e-12 / 1e-14 | 15 |
| （回歸）`golden_zwtv` 全套 | golden_zwtv | `sig` | 走 AVX 路徑仍對 mosqito | 沿用 Phase 3 容差 | 14–15 |

**RED→GREEN 節奏**：先寫 `simd_parity` 測試 → `cargo test --test simd_parity` 應 FAIL（`third_octave_levels_avx2`/`nl_loudness_avx2` 不存在）→ 實作 kernel → GREEN。

## 4. 已知差異風險 / 排查順序

1. **以 scalar 最終版為準**：AVX kernel 照 Phase 3 `nl_lp_step` 的**最終**分支語意寫。若 Phase 3 曾為復刻 mosqito 調整過分支（見 [phase-3](phase-3-zwtv-scalar.md) §4 風險 1/3），blend 結構要同步改。
2. **浮點運算順序**：parity 過不了時先查——FMA 合併點（`fmadd`/`fnmadd` vs 分開乘加）、增益乘在輸入端或輸出端、平滑鏈式 vs 序列式。主計畫 Task 14 有對齊指引。
3. **分支 → mask 對應**：decay 分支 `max(cand, ui)`、u2 二階分支 `min(u2_cand, uo)`、attack hold 條件 `ui <= u2_last`——逐一對照 scalar，勿增刪條件。
4. **unsafe 邊界**：kernel 標 `#[target_feature(enable = "avx2,fma")]` 並文件化 Safety；呼叫點只在 `use_avx2()` 為真時進入。
5. **不做 calc_slopes 的 SIMD**（分支發散，主計畫已排除）——本 phase 無此測試是刻意的，非遺漏。

## 5. 驗收對照

```bash
cd iso532
cargo test simd                  # dispatch 單元測試
cargo test --test simd_parity    # filter bank rtol 1e-10、nl rtol 1e-12
cargo test                       # 全綠（golden 此時走 AVX 路徑 = 雙重驗證）
```

前置：Phase 3 完成且全綠、執行機器支援 AVX2+FMA。詳見 [plans/phase-4](../plans/phases/phase-4-avx2.md)。
