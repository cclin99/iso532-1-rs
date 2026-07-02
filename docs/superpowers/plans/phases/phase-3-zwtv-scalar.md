# Phase 3：時變響度 scalar（loudness_zwtv）

**主計畫：** `docs/superpowers/plans/2026-07-03-iso532-rust-avx.md` 的 **Task 10–12**。實作細節照主計畫。

## 範圍

| 主計畫任務 | 內容 |
|---|---|
| Task 10 | `zwtv/third_octave_levels.rs` scalar：ISO Table A.1/A.2 濾波器組 + 平方 + 3 級平滑 + 2 kHz 抽樣 + dB |
| Task 11 | `zwtv/nonlinear_decay.rs` scalar：雙電容非線性衰減、24× 虛擬升採樣 |
| Task 12 | `zwtv/temporal_weighting.rs`、`loudness_zwtv` 公開 API、`LoudnessTimeVarying`、Annex B 時變（signal 10）驗收 |

## 前置條件

- Phase 2 完成（`core/` 兩模組與 golden 基礎設施已就緒且全綠）。

## 驗收

```bash
cd iso532
cargo test --test golden_zwtv    # third_octave_levels/nl_loudness/temporal_weighting/E2E
cargo test --test annexb         # 加上 signal 10 時變測試
cargo test                       # 全綠
```

## 注意事項

- **Task 11 是本 phase 數值風險最高的模組**：主計畫列了三個已知差異點（初始狀態的 mosqito 環繞行為 `uo_last = core[last]/24`、比較運算子等號方向、uo 衰減 mask 不含 `ui < uo_last` 檢查），失敗時照順序處置；`pulse_1k_70` 與 `step_60_80` 兩個訊號最能暴露問題。
- Task 12 的 xlsx 參考轉換需先用 openpyxl 印出 sheet 結構、對照 mosqito `tests/sq_metrics/loudness/test_loudness_zwtv.py` 的讀法再實作。
- 若 Task 11 為復刻 mosqito 而修改了 scalar 分支邏輯，**必須在程式碼註解記錄最終語意**——Phase 4 的 AVX kernel 要照 scalar 最終版寫。
