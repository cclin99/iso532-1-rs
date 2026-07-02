# Phase 4：AVX2 加速（dispatch + kernels）

**主計畫：** `docs/superpowers/plans/2026-07-03-iso532-rust-avx.md` 的 **Task 13–15**。實作細節照主計畫。

## 範圍

| 主計畫任務 | 內容 |
|---|---|
| Task 13 | `simd/mod.rs`：AVX2+FMA runtime 偵測、`set_force_scalar`（測試/基準用） |
| Task 14 | `third_octave_levels_avx2`：28 頻帶 = 7×f64x4，逐樣本推進，biquad/平方/平滑全 FMA + dispatch |
| Task 15 | `nl_loudness_avx2`：21 頻帶 = 6×f64x4，分支改 compare+blend + dispatch |

## 前置條件

- Phase 3 完成且全綠（AVX 版以 scalar **最終版**語意為準，特別是 nonlinear_decay 若在 Phase 3 有為復刻 mosqito 調整過分支）。
- 執行機器需支援 AVX2+FMA（parity 測試在不支援時會 skip——那就等於沒驗，不可在無 AVX2 的機器上宣告完成）。

## 驗收

```bash
cd iso532
cargo test --test simd_parity    # AVX2 vs scalar：filter bank rtol 1e-10、nl rtol 1e-12
cargo test                       # 全綠（golden 測試此時走 AVX 路徑 = 雙重驗證）
```

## 注意事項

- unsafe 邊界：kernel 函式標 `#[target_feature(enable = "avx2,fma")]` 並文件化 Safety 條件；呼叫點只在 `use_avx2()` 為真時進入。
- parity 過不了時先檢查 scalar/AVX 的浮點運算順序差異（FMA 合併、增益乘在輸入或輸出端、平滑鏈式 vs 序列式）——主計畫 Task 14 有對齊指引。
- 不做 calc_slopes 的 SIMD（分支發散，主計畫已排除）。
