# Annex B 對照一致偏高約 0.15% 的原因

> 對照／Pair: [English](report.en.md) · 來源：zh · 同步 2026-11-05

Claude（Opus 5.5，主代理，非 Astra），2026-11-05 Asia/Taipei。受測：`v0.4.0` = `118322f`（0.4.0 wheel、Astra 2026-11-04 輪的 Rust 輸出）與官方 Annex A C 程式的 CLI。延續 [`2026-11-05-perf-compliance-118322f/`](../2026-11-05-perf-compliance-118322f/report.md) §4.2 的發現。

## 結論

- **偏差不是引擎造成的，而是 WAV 換算成聲壓的慣例不同。** Annex B 工作簿的參考值，跟「數位滿刻度 1.0 = 2√2 Pa」（等於滿刻度正弦 = 100 dB SPL）這個固定換算完全吻合。Annex C 的校準檔 `calibration signal sine 1kHz 60dB.wav` 峰值只有 327 LSB，照同一慣例應為 327.68 LSB，所以它的 RMS 比標示的 60 dB 低 **0.0226 dB**。
- 官方 CLI 依校準檔全段均方值算係數（2.835798 Pa/單位，比 2√2 大 0.26%），Astra 的驗收 harness 和前一份報告的 `compliance.py` 也照這個方式做，於是所有位準都高了 0.0226 dB，**響度因此一致偏高約 0.15%**。
- 改用 2√2 換算後，20 個時變訊號的 N(t) 中位數偏差都是 0.000%～−0.007%，Nmax 偏差 ≤ 0.004%，純音穩態訊號 2、4 是 −0.001%。逐點判準同樣是 0 個點超出。
- 專案內建的 Annex B 測試（`tools/gen_golden.py` → `data/annexb` → `tests/annexb.rs`）本來就用 `wav_calib=2 * 2**0.5`，跟 MoSQITo 1.2.1 的測試相同，所以不受影響。0.4.0 的 C golden（`tools/gen_golden_c.py`）照官方 CLI 用校準檔；Rust 和 C 吃的是同一份輸入，這組比較也不受影響。
- **不需要改程式。** 引擎吃的是以 Pa 為單位的聲壓，換算由整合端負責（README「現階段限制」）。要決定的是：專案對外的 Annex B 對照要採用哪一種換算，以及要不要在文件裡寫明這個 0.0226 dB 的差異。

## 1. 排除過程

| 步驟 | 結果 | 證據 |
|---|---|---|
| Rust 對官方 C（同一份校準後輸入） | N5 差 ≤ 4.5e-4 sone，兩者對工作簿都是 +0.14%～+0.18% | 先前審查的 `AnnexB深入分析.json`（`docs/verification/2026-10-31-F02-5450d39/`）的 `official_c_linear_same_rows`；官方 CLI 自己讀 WAV 和校準檔 |
| 跳過 WAV 和濾波器組（訊號 1，直接輸入 1/3 倍頻程位準） | N 偏差 −0.0007% | 前一份報告 §4.1 |
| 官方 C 穩態路徑（訊號 2–5，time skip 0.2 s） | +0.142%～+0.162% | [official-cli/](official-cli/)、[stationary-compare.json](stationary-compare.json) |
| 官方 C 時變路徑的穩定段（純音 2–4） | +0.142%～+0.189% | 同上 |
| 偏差對參考響度的關係 | 純音約固定 +0.15%；噪音和低響度處較大（訊號 9 在 0.3–1 sone 是 +0.36%） | [bias-vs-level.json](bias-vs-level.json)：符合位準偏移的特徵（接近閾值時響度曲線較陡） |
| 校準官方校準檔後量測位準 | 校準檔各段都是 60.000 dB；訊號 2 是 80.023 dB、訊號 3 是 60.028 dB | [level-check.json](level-check.json) |

所以偏差發生在 WAV → 校準這一步。官方 CLI 的校準程式（`ISO_532-1_main.c` 的 `CalFactor = sqrt(10^(L/10)·I_REF/IntensSum)`）跟我們的作法一致，問題出在校準檔本身跟工作簿採用的換算不一致。

## 2. 校準檔的數字

- 48 kHz、16 bit、單聲道、1.000 s；整數峰值 ±327，RMS 231.1025 LSB。
- 在 2√2 慣例下，60 dB 的 1 kHz 正弦峰值應為 0.01 = 327.68 LSB，RMS 231.7048 LSB。
- RMS 比例：−0.02261 dB。換算係數 2√2 / 2.835798 = 0.997401（−0.260%）。
- 用 2√2 回推標示位準：訊號 2「250 Hz 80 dB」是 80.0003 dB、訊號 3「1 kHz 60 dB」是 60.005 dB；用校準檔回推則是 80.023 dB 和 60.028 dB。（訊號 4「4 kHz 40 dB」兩種回推都偏低約 0.05～0.07 dB，跟這次的偏差無關。）

峰值 327 看起來像是 327.68 被截斷成整數。這只是推論，官方資料沒有說明校準檔怎麼產生。

## 3. 假說檢驗（[rescale_test.py](rescale_test.py)，0.4.0 wheel）

把 Astra 校準後的輸入乘以 0.997401（也就是改用 2√2 換算），重新計算後跟工作簿比較（[rescale-test.json](rescale-test.json)）：

| 訊號 | N(t) 中位數偏差（校準檔 → 2√2） | Nmax 偏差（校準檔 → 2√2） |
|---|---|---|
| 6–13（B.4 合成訊號） | +0.145%～+0.165% → −0.000%～+0.000% | +0.141%～+0.166% → −0.000%～+0.001% |
| 14–25（B.5 技術訊號） | +0.139%～+0.183% → −0.007%～+0.000% | +0.140%～+0.170% → −0.004%～+0.000% |
| 2、4（純音，時變穩定段） | +0.146%／+0.144% → −0.001%／−0.001% | — |

N(t) 中位數只計參考值 ≥ 0.5 sone 的點。兩種換算下，時變 N(t) 都是 0 個點超出逐點判準。

## 4. 影響與選項

- 引擎、0.4.0 發布內容、Annex B 的 PASS 判定都不變：兩種換算都通過，2√2 換算的餘裕更大。
- 前一份報告 §4.2「一致偏高約 0.15%」的描述仍然正確，但要補上原因：那是換算慣例造成的，不是引擎誤差。這一份報告就是那段的補充，前一份交付不修改。
- 待決（不在本輪處理）：
  1. 對外的 Annex B 對照（驗收 harness、未來的報告）要不要統一改用 2√2，或兩種都列出。
  2. 要不要在 README 的精度章節和 `tools/gen_golden_c.py` 的說明裡，寫明兩種換算的 0.0226 dB 差異。
  3. `tools/gen_golden_c.py` 要不要改用 2√2。這會改變 C golden 的輸入，所有 C golden hash 都要重新產生，等同另一輪工作。

## 5. 限制

- 「工作簿用 2√2 產生」是從吻合程度推論出來的（偏差降到 0.000%），官方資料裡沒有直接寫明。
- 這次只比對時變 N(t) 和 Nmax，沒有用 2√2 重算全部 73,116 點的比響度。
- 用的是先前輪次建置的官方 CLI（hash 跟 C-01 補零那一輪的紀錄相符），沒有重新編譯。

## 6. 證據檔案

| 檔案 | 內容 |
|---|---|
| [official-cli/](official-cli/) | 官方 CLI 對訊號 2–5 的穩態與時變輸出（`Loudness.csv`、stdout）、指令、輸入 hash；時變的 `SpecLoudness.csv` 每份 8 MB，只記 hash |
| [stationary_compare.py](stationary_compare.py)、[stationary-compare.json](stationary-compare.json) | 官方 C 穩態與時變穩定段對工作簿 |
| [bias_vs_level.py](bias_vs_level.py)、[bias-vs-level.json](bias-vs-level.json) | 偏差對參考響度的分組 |
| [level_check.py](level_check.py)、[level-check.json](level-check.json) | 校準後的實際位準 |
| [rescale_test.py](rescale_test.py)、[rescale-test.json](rescale-test.json) | 2√2 換算的假說檢驗 |
| [delivery-integrity.json](delivery-integrity.json) | 去識別化後各檔 SHA-256（排除自身） |
