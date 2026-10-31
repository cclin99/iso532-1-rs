# ISO Annex B 數值誤差分析 - Rust+AVX2 對 Python/mosqito

> 對照／Pair: [English](ISO-ANNEXB-NUMERICAL-ERROR-2026-07-04.md) · 來源：en · 同步 2026-11-01

日期：2026-07-04
工作區：<REPO>
參考實作：由 `tools/gen_golden.py` 產生的 Python mosqito 1.2.1 golden 資料
Rust 路徑：`iso532` crate，目前的 Rust+AVX2 最佳化 ZWTV 管線
ISO 參考來源：`data/annexb/` 中的 Annex B CSV/XLSX 資料

## 摘要

相對於 ISO Annex B 參考值，Rust+AVX2 與 Python/mosqito 在 ISO 符合性尺度上數值無法區分。可觀察到的對 ISO 參考值的差異，主要來自 ISO Annex B 的容差／參考值層與 mosqito 的參考語義，而非 Rust、AVX2、rayon 或近期的資料佈局最佳化。

Rust+AVX2 相對於 Python/mosqito 只增加極小的殘餘誤差：

- 總響度 `N` / `N(t)`：對 mosqito golden 為 0 到約 `1.6e-14` sone。
- 比響度 `N_specific`：對 mosqito golden 觀察到的最差值約 `1.3e-9` sone/Bark。
- AVX2 對 Rust scalar 的 `N(t)`：在量測的 golden 集合上位元相同。
- AVX2 對 Rust scalar 的 `N_specific(t)`：觀察到的最差值約 `1.4e-9` sone/Bark。

這些殘餘值比 ISO Annex B 符合性容差小許多個數量級，該容差為 `abs(error) <= 0.1 + 0.05 * abs(reference)`。

> 2026-10-31 更正（V-01）：官方 Annex B workbook 採用 max 規則 `abs(error) <= max(0.1, 0.05 * abs(reference))`，它永遠不會比上面引用的加法式更寬鬆。本文件中的數字不變；repository 的測試已在 V-01 中切換為 max 規則。

## ISO Annex B 總響度

| 案例 | ISO 參考值 | Python/mosqito golden | Rust+AVX2 | 對 ISO 的絕對差 | 對 ISO 的相對差 |
|---|---:|---:|---:|---:|---:|
| Annex B 訊號 3，穩態 `N` | 4.019 | 4.052 | 約 4.052 | 0.033 sone | 0.821% |
| Annex B 訊號 5，穩態 `N` | 10.498 | 10.418 | 約 10.418 | 0.080 sone | 0.762% |
| Annex B 訊號 10，時變 `N(t)` 最大絕對值 | XLSX 曲線 | mosqito 曲線 | 約為 mosqito 曲線 | 1.976e-4 sone | 見附註 |

對訊號 10，最大的相對誤差出現在 ISO 參考值接近零處：Rust/mosqito `5.031e-5` 對 ISO `1.0e-4`，相對約 49.7%，但絕對值僅 `4.97e-5` sone。這遠在 Annex B 絕對容差項 `0.1` sone 之內。

## ISO Annex B 比響度

| 案例 | 對 ISO 的最差絕對差 | Bark 索引 | Rust/mosqito 值 | ISO 值 | 對 ISO 的最差相對差 |
|---|---:|---:|---:|---:|---:|
| Annex B 訊號 3，`N_specific` | 0.01486 sone/Bark | 66 | 0.35656 | 0.34170 | 76.8%，位於接近零的點 |
| Annex B 訊號 5，`N_specific` | 0.00986 sone/Bark | 66 | 0.40514 | 0.41500 | 3.19% |

訊號 3 的大相對數字出現在 ISO 值極小處：Rust/mosqito `0.01025` 對 ISO `0.0058`，絕對差 `0.00445` sone/Bark。ISO Annex B 使用 `0.1` 的絕對容差項，因此這仍穩穩落在符合範圍內。

## Rust+AVX2 對 Python/mosqito golden

| 輸出 | 最大絕對誤差 | 最大相對誤差 | 解讀 |
|---|---:|---:|---|
| `zwst` 總響度 `N` | 0 | 0 | 經 ISO/mosqito 總響度量化後精確相同。 |
| `zwst` `N_specific` | 8.2e-14 | 2.9e-12 | 浮點雜訊底。 |
| `zwtv` `N(t)` | 1.6e-14 | 3.8e-15 | 浮點雜訊底。 |
| `zwtv` `N_specific(t)` | 1.3e-9 | 3.0e-9 | 最差案例是接近 `calc_slopes` `r8()` 分支邊界的階躍訊號。 |

## Rust+AVX2 對 Rust Scalar

| 輸出 | 最大絕對誤差 | 最大相對誤差 | 解讀 |
|---|---:|---:|---|
| `zwtv` `N(t)` | 0 | 0 | 在量測的 golden 集合上位元相同。 |
| `zwtv` `N_specific(t)` | 1.4e-9 | 3.2e-9 | 預期的 FMA／分支邊界殘餘；由 SIMD parity 測試守住。 |

## 理論誤差尺度

| 層 | 典型尺度 |
|---|---:|
| ISO Annex B 符合性容差 | 參考值的 `0.1 + 5%` |
| `calc_slopes` 總響度量化，`N <= 16` | 最大 `0.0005` sone |
| `calc_slopes` 總響度量化，`N > 16` | 最大 `0.005` sone |
| Rust+AVX2 對 Python/mosqito 總響度殘餘 | `0` 到 `1e-14` sone |
| Rust+AVX2 對 Python/mosqito 比響度殘餘 | `1e-14` 到 `1e-9` sone/Bark |
| 1 到 10 sone 附近的 f64 ULP 雜訊 | 約 `1e-16` 到 `1e-15` |

實務上的結論是：就本專案而言，Rust+AVX2 在數值上等同於 Python/mosqito。任何對 ISO Annex B 參考值可見的差異，都是 mosqito 本身已存在的參考值／符合性層差異，而非 Rust+AVX2 最佳化工作引入的誤差。

## 重現附註

上述對 ISO 參考值的差異是由本機 repository 的產物計算而得：

- `data/golden/annexb_sig3/N.bin`
- `data/golden/annexb_sig5/N.bin`
- `data/golden/annexb_sig10/N_time.bin`
- `data/golden/annexb_sig10/tv_nref.bin`
- `data/golden/annexb_sig10/tv_time.bin`
- `data/annexb/test_signal_3.csv`
- `data/annexb/test_signal_5.csv`

Rust+AVX2 對 mosqito 與 AVX2 對 scalar 的殘餘值記錄於 `docs/DESIGN-DEVELOPMENT-2026-07-04.md`，並由 golden 與 SIMD parity 測試套件守住。
