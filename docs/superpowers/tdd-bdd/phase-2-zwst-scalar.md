# Phase 2 TDD/BDD：穩態響度 scalar（loudness_zwst）

**對應計畫：** [plans/phases/phase-2-zwst-scalar.md](../plans/phases/phase-2-zwst-scalar.md)（主計畫 Task 4–9）　**狀態：** ✅ 已實作
**測試檔：** `tests/golden_dsp.rs`、`tests/golden_zwst.rs`、`tests/golden_core.rs`、`tests/annexb.rs`、`tests/api_errors.rs`

## 1. 測試策略摘要

穩態路徑由「DSP 基礎層 → zwst 頻譜 → core 響度 → 斜率積分 → 公開 API」串成，採**逐階段 golden 夾擊 + 端到端 + ISO 合規**三層：

1. **DSP scipy parity**（`golden_dsp`）：`sosfilt`/`sosfiltfilt`/`decimate` 對 scipy 固定輸入的 golden，容差最緊（`1e-12`），把數值誤差鎖在最底層。
2. **zwst 逐階段 mosqito parity**（`golden_zwst` / `golden_core`）：`noct_spectrum_rms` → `spec_to_db` → `main_loudness`(free/diffuse) → `calc_slopes`，每一階的中間陣列都對 mosqito golden 比對，任何一階錯都能單點定位。
3. **端到端 + ISO Annex B**：`loudness_zwst` 整段對 mosqito 的 `N`/`N_specific`；再對 ISO 官方 Annex B signal 3/5 的 5%/0.1 合規。

> `golden_core.rs` 與 `golden_zwst.rs` 對 `main_loudness`/`calc_slopes` 有**重疊覆蓋**（Phase 2 並行開發時的兩套 harness）——保留為冗餘防護，兩者同綠才算過。

## 2. BDD 行為情境（Gherkin）

### Feature: SOS 濾波基礎層（dsp/sos.rs、dsp/filtfilt.rs）

```gherkin
Scenario: 雙二階級聯濾波對齊 scipy sosfilt
  Given scipy 對 4096 點輸入用 Chebyshev-I SOS 的 golden
  When 呼叫 sosfilt(&cheby_sos, &mut x)
  Then 輸出對 dsp_sosfilt_y.bin，rtol<=1e-12, atol<=1e-15

Scenario: 零相位前後向濾波對齊 scipy sosfiltfilt（odd padding）
  Given 同一輸入與 SOS
  When 呼叫 sosfiltfilt(&cheby_sos, &x)
  Then 輸出對 dsp_sosfiltfilt_y.bin，rtol<=1e-9, atol<=1e-12

Scenario: 抽取降採樣對齊 scipy decimate(q=10)
  Given 同一輸入
  When 呼叫 decimate(&x, 10)
  Then 輸出對 dsp_decimate_q10.bin，rtol<=1e-9, atol<=1e-12
```

### Feature: 1/3 倍頻程頻譜（zwst::noct_spectrum_rms / spec_to_db）

```gherkin
Scenario: 28 頻帶 RMS 對齊 mosqito noct_spectrum
  Given sine_1k_60 / sine_250_80 / white_60 訊號
  When 呼叫 noct_spectrum_rms(&x)
  Then 各帶 RMS 對 spec_third_amp.bin，rtol<=1e-7, atol<=1e-12

Scenario: 振幅轉 dB 對齊 mosqito amp2db（ref=2e-5）
  Given 上一步的振幅頻譜
  When 呼叫 spec_to_db(&spec)
  Then 對 spec_third_db.bin，rtol<=1e-12, atol<=1e-12
```

### Feature: 核心響度（core::main_loudness，ISO 532-1 A.3）

```gherkin
Scenario: free / diffuse 場核心響度對齊 mosqito
  Given sine_1k_60 / sine_250_80 / sine_4k_60 / white_60 的 spec_third_db
  When 呼叫 main_loudness(&spec_db, Free) 與 Diffuse
  Then 21 帶核心響度分別對 nm_free.bin / nm_diffuse.bin，rtol<=1e-9, atol<=1e-15

Scenario: 低頻帶超過 120 dB 時拒絕（Zwicker 法不適用）
  Given 一個第 3 帶為 121 dB 的頻譜
  When 呼叫 main_loudness(&spec, Free)
  Then 回傳 Err(Iso532Error::LevelExceeds120dB)
```

### Feature: 斜率積分與端到端（core::calc_slopes、loudness_zwst）

```gherkin
Scenario: 遮蔽斜率 + Bark 積分對齊 mosqito
  Given 各訊號的 nm_free（21 帶核心響度）
  When 呼叫 calc_slopes(&nm)
  Then 總響度 N 對 N.bin，|ΔN| <= 1e-9 + 1e-6·|N|
  And 240 點 specific loudness 對 N_specific.bin，rtol<=1e-6, atol<=1e-9

Scenario: 穩態端到端對齊 mosqito（含 Annex B 訊號）
  Given sine_1k_60 … annexb_sig3 / annexb_sig5 的原始訊號
  When 呼叫 loudness_zwst(&x, 48000.0, Free)
  Then N 對 N.bin，|ΔN| <= 1e-3 + 1e-6·|N|
  And n_specific 對 N_specific.bin，rtol<=1e-6, atol<=1e-9
  And bark_axis.len() == 240
```

### Feature: ISO Annex B 穩態合規（tests/annexb.rs）

```gherkin
Scenario: Test signal 3（1 kHz 60 dB）符合 ISO 參考
  Given annexb_sig3 訊號與 test_signal_3.csv（240 點 specific）
  When 呼叫 loudness_zwst(&sig, 48000.0, Free)
  Then N isoclose 4.019（5% 或 0.1）
  And n_specific 對 CSV isoclose

Scenario: Test signal 5（pinknoise 60 dB）符合 ISO 參考
  Given annexb_sig5 訊號與 test_signal_5.csv
  When 呼叫 loudness_zwst(&sig, 48000.0, Free)
  Then N isoclose 10.498（5% 或 0.1）
  And n_specific 對 CSV isoclose
```

### Feature: 公開 API 錯誤路徑（tests/api_errors.rs）

```gherkin
Scenario: 拒絕非 48 kHz 取樣率
  When loudness_zwst(&x, 44100.0, Free)
  Then Err(UnsupportedSampleRate(44100.0))

Scenario: 拒絕過短訊號（< 4800 樣本）
  When loudness_zwst(&[0.0; 4799], 48000.0, Free)
  Then Err(SignalTooShort { got: 4799, need: 4800 })
```

## 3. TDD 測試清單（RED→GREEN）

| 測試名 | 檔案 | 輸入(golden) | 預期 | 容差 (rtol/atol) | 對應 Task |
|---|---|---|---|---|---|
| `sosfilt_matches_scipy` | golden_dsp | `_dsp/dsp_x` + `dsp_cheby_sos` | `dsp_sosfilt_y` | 1e-12 / 1e-15 | 4 |
| `sosfiltfilt_matches_scipy` | golden_dsp | 同上 | `dsp_sosfiltfilt_y` | 1e-9 / 1e-12 | 5 |
| `decimate_matches_scipy` | golden_dsp | `_dsp/dsp_x` | `dsp_decimate_q10` | 1e-9 / 1e-12 | 5 |
| `noct_spectrum_matches_mosqito` | golden_zwst | `sig` | `spec_third_amp` | 1e-7 / 1e-12 | 6 |
| `spec_to_db_matches_mosqito_amp2db` | golden_zwst | `spec_third_amp` | `spec_third_db` | 1e-12 / 1e-12 | 6 |
| `main_loudness_matches_mosqito` | golden_zwst | `spec_third_db` | `nm_free` / `nm_diffuse` | 1e-9 / 1e-15 | 7 |
| `main_loudness_rejects_over_120db` | golden_zwst | 手構頻譜(band3=121) | `Err(LevelExceeds120dB)` | 精確 | 7 |
| `main_loudness_matches_..._core_loudness` | golden_core | `spec_third_db` | `nm_free`/`nm_diffuse` | 1e-9 / 1e-15 | 7（冗餘）|
| `main_loudness_rejects_..._above_120_db` | golden_core | 手構頻譜 | `Err(LevelExceeds120dB)` | 精確 | 7（冗餘）|
| `calc_slopes_matches_mosqito` | golden_zwst | `nm_free` | `N` / `N_specific` | N: 1e-9+1e-6rel；spec 1e-6 / 1e-9 | 8 |
| `calc_slopes_matches_..._loudness` | golden_core | `nm_free` | `N` / `N_specific` | 同上 | 8（冗餘）|
| `zwst_end_to_end_matches_mosqito` | golden_zwst | `sig`（6 訊號含 sig3/5）| `N` / `N_specific` | N: 1e-3+1e-6rel；spec 1e-6 / 1e-9 | 9 |
| `annexb_stationary_signal3_1khz_60db` | annexb | `annexb_sig3/sig` + CSV | N≈4.019；spec | isoclose(5%/0.1) | 9 |
| `annexb_stationary_signal5_pinknoise_60db` | annexb | `annexb_sig5/sig` + CSV | N≈10.498；spec | isoclose(5%/0.1) | 9 |
| `loudness_zwst_rejects_unsupported_sample_rate` | api_errors | `44100.0` | `Err(UnsupportedSampleRate)` | 精確 | 9 |
| `loudness_zwst_rejects_short_signal` | api_errors | `[0.0; 4799]` | `Err(SignalTooShort)` | 精確 | 9 |

## 4. 已知差異風險 / 排查順序

失敗時照主計畫每個 golden 附的「已知差異風險」清單，**以 golden 為準**：

1. **DLL 查表向量化差異**（`main_loudness`，主計畫 item 1071）：mosqito 的 dll 選擇只掃到 `j=6`；低頻帶 > `rap[6]-dll[6]`（>~100 dB）時 mosqito 給 0 而非 `dll[7]`。此差異在計畫審查時已記錄並復刻。
2. **`round(x, 8)` 比較語意**（`calc_slopes`）：mosqito 用 `np.round(x, 8)` 決定上升/下降分支，Rust 端 `r8()` 復刻；比較運算子等號方向（`<` vs `<=`）是首要嫌疑。
3. **SOS 增益擺放**（`noct_spectrum`）：低頻帶走 decimate 路徑，差異大先查 `NOCT_DECIM_Q` 生成值；僅 rtol 略超則為 SOS 增益乘在輸入/輸出端的順序差。
4. **Annex B 參考值**：signal 3 ISO 值為 **4.019**（非計畫初稿的 4.25）、signal 5 為 **10.498**——審查時已對照 CSV 更正，勿改回。
5. **sosfiltfilt padlen**：差異略超容差先印 scipy 實際 padlen 比對，並確認 `decimate` 為 `zero_phase=True`。

## 5. 驗收對照

```bash
cd iso532
cargo test --test golden_dsp     # sosfilt/sosfiltfilt/decimate scipy parity
cargo test --test golden_zwst    # noct/spec_to_db/main_loudness/calc_slopes/E2E
cargo test --test golden_core    # main_loudness/calc_slopes 冗餘覆蓋
cargo test --test annexb         # 穩態 signal 3/5 合規
cargo test --test api_errors     # zwst 錯誤路徑
cargo test                       # 全綠
```

前置：Phase 1 勘誤補完（`annexb_sig3/` golden 已產出）。詳見 [plans/phase-2](../plans/phases/phase-2-zwst-scalar.md)。
