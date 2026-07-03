# Phase 2：穩態響度 scalar（loudness_zwst）

**主計畫：** `docs/superpowers/plans/2026-07-03-iso532-rust-avx.md` 的 **Task 4–9**。實作細節照主計畫。

## 範圍

| 主計畫任務 | 內容 |
|---|---|
| Task 4 | `dsp/sos.rs`：sosfilt、sosfilt_zi、onepole |
| Task 5 | `dsp/filtfilt.rs`：sosfiltfilt（odd padding）、decimate |
| Task 6 | `zwst/`：noct_spectrum_rms（28 頻帶 1/3 倍頻程 RMS）、spec_to_db |
| Task 7 | `core/main_loudness.rs`（含 >120 dB 錯誤路徑） |
| Task 8 | `core/calc_slopes.rs`（遮蔽斜率 + Bark 積分） |
| Task 9 | `loudness_zwst` 公開 API、`LoudnessStationary`、Annex B 穩態合規測試 |

## 前置條件

- Phase 1 完成：`data/golden/` 與 `data/annexb/` 存在、`tables_noct.rs` 已生成、`cargo test` 綠。
- **Phase 1 勘誤補完（開工前必做）**：`tools/gen_golden.py` 的 Test signal 3 檔名改為 `Test signal 3 (1 kHz 60 dB)_44100Hz.wav`（主計畫 Task 2 已更正；mosqito `load()` 會重採樣到 48 kHz），重跑 `.venv/Scripts/python tools/gen_golden.py`，確認 `data/golden/annexb_sig3/` 產出且 `N.bin` ≈ 4.2——Task 9 的 golden/Annex B 測試依賴它。

## 驗收

```bash
cd iso532
cargo test --test golden_dsp     # sosfilt/sosfiltfilt/decimate scipy parity
cargo test --test golden_zwst    # noct/main_loudness/calc_slopes/E2E 全過
cargo test --test annexb         # 穩態 signal 3 與 5 合規（rtol 5%, atol 0.1）
cargo test                       # 全綠
```

## 注意事項

- 每個 golden 測試附有「已知差異風險」清單（比較運算子方向、mosqito round(x,8) 語意、初始化差異）——失敗時照清單順序排查，**以 golden 為準**，不要憑推理改容差了事。
- 容差放寬需在測試註解寫明原因（哪個浮點運算順序差異）。
- Task 9 的 Annex B csv parser 要先看實際檔案格式再定欄位（主計畫有指示）。
