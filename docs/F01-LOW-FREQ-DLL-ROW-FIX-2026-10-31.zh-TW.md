# F-01：Annex A 低頻修正略過了 DLL 表的最後一列

> 對照／Pair: [English](F01-LOW-FREQ-DLL-ROW-FIX-2026-10-31.md) · 來源：en · 同步 2026-11-01

- 日期：2026-10-31
- 範圍：`iso532/src/core/main_loudness.rs`（`main_loudness_unchecked`），由批次 ZWST、
  批次 ZWTV 與 `ZwtvStream`（經 `main_loudness_clamped`）共用
- 來源：`docs/修正報告.md` 的發現 F-01（對照官方 ISO 532-1 Annex A C 程式的獨立
  審核），於本次變更中驗證並修正；修正後的獨立驗證見
  `docs/修正後獨立驗證報告.md`
- 狀態：已修正；在有界的輸入範圍內數值行為改變
- 定位：下方的 MoSQITo 比較是驗證過程中的發現，加上本專案的目前判斷；並非對
  MoSQITo 的裁定

## 發現

ISO 532-1 Annex A（`corr_third_octave_intensities`，與 Zwicker/Fastl 1991 年的 BASIC
程式相同）以下列方式為 11 個低頻帶各自選取 RAP 範圍

```c
j = 0;
while (j < 7 && level > RAP[j] - DLL[j][band]) j++;
corrected = level + DLL[j][band];
```

因此任何高於第七個門檻的位準都會取得最後一列 `DLL[7]`。

Rust 移植版沿用了 MoSQITo 1.2.1，而後者以向量化方式取代該迴圈時，迭代的是
`for i in arange(1, dll_mat.shape[0] - 1)`，因此走不到第 7 列。高於第七個門檻時，
預設值 `0` 便留作修正量。MoSQITo 上游 `master` 也有同樣的迴圈（2026-10-31 查核；
上游最後一次 commit 為 2024-04-22）。目前判斷：遵循 Annex A，即兩個專案都引用的
參考。

受影響範圍（位準嚴格高於 `RAP[6] - DLL[6][band]`，上至 120 dB 的有效上限）：

| 頻帶 | 中心頻率 | 門檻 | 修正前的修正量 | 修正後的修正量（Annex A） |
|---|---|---:|---:|---:|
| 0 | 25 Hz | 118 dB | 0 | -15 dB |
| 1 | 31.5 Hz | 112 dB | 0 | -10 dB |
| 2 | 40 Hz | 109 dB | 0 | -8 dB |
| 3 | 50 Hz | 106 dB | 0 | -4 dB |
| 4 | 63 Hz | 102 dB | 0 | -2 dB |
| 6 | 100 Hz | 103 dB | 0 | -3 dB |
| 7 | 125 Hz | 101 dB | 0 | -1 dB |
| 9 | 200 Hz | 101 dB | 0 | -1 dB |

頻帶 5、8、10 的 `DLL[7] = 0`，從未受影響。位準等於或低於第七個門檻時選到的列與
之前相同；由於每個頻帶的門檻都嚴格遞增（現已由單元測試釘住），舊的 xor 寫法與
Annex A 迴圈在該範圍內位元逐一一致。

## 重現（修正前／修正後）

參考值來自獨立審核所執行的官方 ISO 532-1 Annex A C 程式（`docs/修正報告.md` §3.2；
C 原始碼不在本 repository 中再散布）。28 頻帶的數值則是在此以 Annex A 迴圈對 crate
自己的表重新推導而得。

| 案例 | 修正前 | 修正後 | Annex A C | 容差（max(0.1, 5 %)） |
|---|---:|---:|---:|---|
| 28 頻帶，頻帶 0 = 118.000001 dB，其餘 -60 dB，自由場 | 154.93 sone | 52.51 sone | 52.514908816 | 通過 |
| 2 s 正弦波，25 Hz，119 dB SPL，ZWST 自由場 | 165.19 sone | 容差內 | 56.704172426 | 通過 |
| 同一正弦波，ZWTV 最大 N | 172.13 sone | 56.877 sone | 56.878693537 | 通過 |
| 同一正弦波，串流 warm-up 後最大 N | 171.97 sone | 56.555 sone | 56.878693537 | 通過（起始後的窗） |

串流與批次的數值在 warm-up 後逐幀一致到 <= 1e-6（在此訊號上，要到第 597 幀起才到
<= 1e-9；`N_WARMUP_FRAMES = 580` 是在合成測試訊號上凍結的，此處不更動）。

## 修正

`low_freq_dll_row(level, band)` 逐字實作 Annex A 迴圈，取代以 xor 為基礎的選取。
未更動任何表、門檻方向、功率轉換或後續階段。

## 新增的驗證

- 單元（`main_loudness.rs`）：每個頻帶的門檻嚴格遞增；在每個門檻、低一個 ULP 與
  高一個 ULP 處的列選取，涵蓋全部 11 個頻帶與 8 列；在第 7 列與第 0 列的飽和；
  NaN 對應到第 0 列（有文件記載，但不代表認可非有限輸入）；最後一列在 120 dB 以下
  可達；clamped 串流變體在 119 dB 時等於批次變體。
- 整合（`tests/low_freq_correction.rs`，自足，已加入 CI）：上述四個重現列、
  118 dB 嚴格門檻階躍、120 dB 接受／120 dB + ULP 拒絕的契約、擴散場，以及
  warm-up 後串流對批次的追蹤。
- 回歸：九個 MoSQITo golden fixture、Annex B 訊號 3/5/10、SIMD parity、決定性、
  凍結 hash 關卡、FFI 與 Python parity 套件（執行紀錄見 commit 訊息）。

## 影響

- MoSQITo 1.2.1 parity 現在有了範圍限定：在上述範圍之外成立。低頻帶位準高於第七個
  門檻的輸入，預期會與 MoSQITo 不同，必須以 Annex A 判斷。
- panel（`iso532-rs-panel`）以 git tag 釘住 core `v0.1.0`，不受本 commit 影響；在其
  相依版本升級之前維持舊行為。
- F-02（批次非線性衰減以最後一幀作為種子）是另一項獨立且有文件記載的 MoSQITo
  相容性選擇，此處刻意不觸碰。
