# Phase 9 TDD/BDD：Apple M 系列 NEON kernel（aarch64）

**對應：** [ROADMAP §5](../../ROADMAP.md)　**狀態：** 🎨 設計（相依 phase-4 AVX2 kernel 定案）
**規劃測試檔：** `tests/simd_parity.rs`（複用，加 NEON 分支）

> NEON kernel 是 AVX2 kernel 的機械性移植。本文件的測試策略幾乎與 [phase-4](phase-4-avx2.md) 同構——差別在向量寬度與「baseline feature 不需 runtime 偵測」。

## 1. 測試策略摘要

aarch64 上 NEON 是 128-bit（`f64x2`）：28 頻帶 = 14 個向量（AVX2 為 7）、21 帶 = 11 個向量。FMA 用 `vfmaq_f64`，分支消除用 `vmaxq_f64`/`vminq_f64`/`vbslq_f64`，與 AVX2 kernel **一一對應**。驗證主軸同 phase-4：

1. **NEON vs scalar parity**：`third_octave_levels_neon` 對 `_scalar`、`nl_loudness_neon` 對 `_scalar`，容差同 AVX2（`1e-10`/`1e-12`）。
2. **golden 雙路徑**：aarch64 機器上 golden 走 NEON = 對 mosqito 的獨立驗證。
3. **無 runtime 偵測**：NEON 是 aarch64 baseline，`#[cfg(target_arch = "aarch64")]` 直接編入——dispatch 比 x86 簡單，**沒有 skip 分支**（在 aarch64 上一定執行）。

> ⚠️ 平台鏡像陷阱：在 Apple M 上跑 `cargo test` 全綠**只證明 aarch64（scalar + NEON）正確**，不代表驗過 x86 AVX2；反之亦然。SIMD 正確性是**每架構各驗一次**。

## 2. BDD 行為情境（Gherkin）

### Feature: NEON 濾波器組 kernel（third_octave_levels_neon）

```gherkin
Scenario: 28 頻帶 = 14×f64x2 的 NEON 濾波對齊 scalar
  Given deterministic 偽隨機 1 秒訊號（同 phase-4 的 LCG）
  And 於 aarch64 目標編譯執行
  When 分別呼叫 third_octave_levels_scalar 與 third_octave_levels_neon
  Then 逐元素 rtol<=1e-10, atol<=1e-12

Scenario: aarch64 上無 skip（baseline feature）
  Given target_arch == aarch64
  When 執行 filter_bank_neon_matches_scalar
  Then 一定實跑（NEON 無需 runtime 偵測，不會被跳過）
```

### Feature: NEON 非線性衰減 kernel（nl_loudness_neon）

```gherkin
Scenario: 21 頻帶 NEON 分支改 vbslq 對齊 scalar
  Given 合成 core loudness（21 帶 × 500 frame，含攻擊與衰減）
  And 於 aarch64 目標
  When 分別呼叫 nl_loudness_scalar 與 nl_loudness_neon
  Then 逐元素 rtol<=1e-12, atol<=1e-14

Scenario: vmax/vmin/vbsl 決策與 scalar 分支一一對應
  Given nl_lp_step 最終版分支語意（同 AVX2 kernel 依據）
  When NEON kernel 用 vmaxq/vminq/vbslq 表達
  Then 選擇與 scalar 完全一致（parity 容差內）
```

### Feature: golden 雙路徑（aarch64 回歸）

```gherkin
Scenario: NEON 路徑下 golden 仍對齊 mosqito
  Given aarch64 機器、golden .bin（LE，跨平台共用）
  When 執行 cargo test --test golden_zwtv
  Then third_octave_levels / nl_loudness 走 NEON 仍全過
```

## 3. TDD 測試清單（RED→GREEN，規劃）

| 測試名 | 檔案 | 輸入 | 預期 | 容差 | 目標 |
|---|---|---|---|---|---|
| `filter_bank_neon_matches_scalar` | simd_parity | LCG 48000 樣本 | neon == scalar | 1e-10/1e-12 | aarch64 |
| `nl_loudness_neon_matches_scalar` | simd_parity | 合成 21×500 core | neon == scalar | 1e-12/1e-14 | aarch64 |
| （回歸）`golden_zwtv` 全套 | golden_zwtv | `sig` | 走 NEON 對 mosqito | 沿用 Phase 3 | aarch64 |

## 4. 已知差異風險 / 排查順序

1. **前置：AVX2 kernel 定案**：NEON 照 phase-4 AVX2 kernel 結構抄；若 AVX2 kernel 尚在調 blend，NEON 不要先寫（會跟著改）。
2. **向量寬度換算**：AVX2 的 7 個 `f64x4` → NEON 的 14 個 `f64x2`；padding lane 數不同（21 帶：AVX2 6×4 有 3 padding、NEON 11×2 有 1 padding）——lane→band 映射要重算。
3. **intrinsic 對應表**：`_mm256_fmadd_pd`→`vfmaq_f64`、`_mm256_max_pd`→`vmaxq_f64`、`_mm256_blendv_pd`→`vbslq_f64`（注意 vbsl 的 mask 語意與 blendv 引數順序差異）。
4. **cfg 隔離**：NEON kernel 在 `#[cfg(target_arch = "aarch64")]` 內；x86 端整個模組不參與編譯。`simd_parity` 的 NEON 測試也用同 cfg 包住，x86 上不編。

## 5. 驗收對照（規劃）

```bash
# 於 Apple M / aarch64 Linux：
cargo test --test simd_parity    # NEON vs scalar（無 skip，一定執行）
cargo test                       # golden 走 NEON = 雙重驗證
```

CI 建議：GitHub Actions 加 `macos-latest`（M 系列 runner）job 驗 aarch64 scalar/NEON。執行順序：ROADMAP 未強制排序，但 phase-8 若要在 Apple M 上達即時，需先有 NEON kernel。
