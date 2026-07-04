# Phase 3 TDD/BDD：時變響度 scalar（loudness_zwtv）

**對應計畫：** [plans/phases/phase-3-zwtv-scalar.md](../plans/phases/phase-3-zwtv-scalar.md)（主計畫 Task 10–12）　**狀態：** ✅ 已實作
**測試檔：** `tests/golden_zwtv.rs`、`tests/annexb.rs`、`tests/api_errors.rs`

## 1. 測試策略摘要

時變路徑：`third_octave_levels`（ISO Table A.1/A.2 濾波器組 + 平方 + 三級平滑 + 2 kHz 抽樣 + dB）→ `main_loudness`（沿用 Phase 2，逐 frame）→ `nonlinear_decay`（雙電容非線性衰減，24× 虛擬升採樣）→ `calc_slopes` → `temporal_weighting` → `loudness_zwtv`。驗證同樣**逐階段 mosqito golden + 端到端 + ISO Annex B 時變**，但多兩個時變特有重點：

1. **`nl_loudness` 是本 phase 數值風險最高的模組**——雙電容衰減對初始狀態與比較運算子極敏感。用 `pulse_1k_70`、`step_60_80` 兩個含攻擊/衰減的訊號專門暴露問題，容差 `1e-6/1e-9`。scalar 實作明確復刻 mosqito `col-1` wraparound 初始狀態與 mask 順序，**供 Phase 4 AVX kernel 逐行對齊**。
2. **Annex B signal 10 三重驗證**：同時比對 mosqito `N_time` parity、ISO xlsx **時間軸**（`1e-12` 近乎精確，因已改用固定樣本網格）、ISO xlsx `N(t)` 5%/0.1 合規。

## 2. BDD 行為情境（Gherkin）

### Feature: 時變 1/3 倍頻程位準（zwtv::third_octave_levels_scalar）

```gherkin
Scenario: ISO 濾波器組逐時框位準對齊 mosqito
  Given sine_1k_60 / pulse_1k_70 / step_60_80 / white_60 訊號
  When 呼叫 third_octave_levels_scalar(&x)
  Then 回傳 (levels, n_time)，n_time == golden.len()/28
  And levels 對 third_octave_level.bin，rtol<=1e-7, atol<=1e-12
```

### Feature: 非線性衰減（zwtv::nonlinear_decay，數值高風險）

```gherkin
Scenario: 雙電容非線性衰減對齊 mosqito
  Given 各訊號的 core_loudness.bin（21 帶 × n_time 核心響度）
  When 呼叫 nl_loudness_scalar(&core, n_time)
  Then 對 nl_loudness.bin，rtol<=1e-6, atol<=1e-9

Scenario: 攻擊/衰減暴露初始狀態與分支語意
  Given pulse_1k_70（脈衝，急攻擊後衰減）與 step_60_80（位準跳階）
  When 執行 nl_loudness_scalar
  Then 結果與 mosqito 一致（初始 uo_last = core[last]/24 wraparound、
       比較運算子等號方向、uo 衰減 mask 不含 ui<uo_last 檢查 三點皆復刻）
```

### Feature: 時間權重與端到端（temporal_weighting、loudness_zwtv）

```gherkin
Scenario: 時間權重濾波對齊 mosqito
  Given pulse_1k_70 / step_60_80 / white_60 的 loudness_raw.bin
  When 呼叫 temporal_weighting(&loud)
  Then 對 filt_loudness.bin，rtol<=1e-9, atol<=1e-12

Scenario: 時變端到端對齊 mosqito（含 Annex B signal 10）
  Given sine_1k_60 / pulse_1k_70 / step_60_80 / annexb_sig10 原始訊號
  When 呼叫 loudness_zwtv(&x, 48000.0, Free)
  Then n（= N(t)）對 N_time.bin，rtol<=1e-6, atol<=1e-9
  And n_specific 對 N_spec_time.bin，rtol<=1e-6, atol<=1e-9
  And bark_axis.len() == 240
```

### Feature: ISO Annex B 時變合規（tests/annexb.rs）

```gherkin
Scenario: Test signal 10（tone pulse 1kHz 10ms 70dB）三重驗證
  Given annexb_sig10 訊號、mosqito N_time.bin、ISO xlsx tv_time.bin / tv_nref.bin
  When 呼叫 loudness_zwtv(&sig, 48000.0, Free)
  Then N(t) 對 mosqito N_time，rtol<=1e-6, atol<=1e-9
  And time_axis 對 ISO xlsx tv_time，rtol<=1e-12, atol<=1e-12（固定樣本網格）
  And N(t) 對 ISO xlsx tv_nref isoclose（5% 或 0.1）
```

### Feature: 公開 API 錯誤路徑（tests/api_errors.rs）

```gherkin
Scenario: 拒絕非 48 kHz 取樣率
  When loudness_zwtv(&x, 44100.0, Free)
  Then Err(UnsupportedSampleRate(44100.0))

Scenario: 拒絕過短訊號
  When loudness_zwtv(&[0.0; 4799], 48000.0, Free)
  Then Err(SignalTooShort { got: 4799, need: 4800 })
```

## 3. TDD 測試清單（RED→GREEN）

| 測試名 | 檔案 | 輸入(golden) | 預期 | 容差 (rtol/atol) | 對應 Task |
|---|---|---|---|---|---|
| `third_octave_levels_matches_mosqito` | golden_zwtv | `sig`（4 訊號）| `third_octave_level` + n_time | 1e-7 / 1e-12 | 10 |
| `nl_loudness_matches_mosqito` | golden_zwtv | `core_loudness` | `nl_loudness` | 1e-6 / 1e-9 | 11 |
| `temporal_weighting_matches_mosqito` | golden_zwtv | `loudness_raw`（3 訊號）| `filt_loudness` | 1e-9 / 1e-12 | 12 |
| `zwtv_end_to_end_matches_mosqito` | golden_zwtv | `sig`（含 annexb_sig10）| `N_time` / `N_spec_time` | 1e-6 / 1e-9 | 12 |
| `annexb_timevarying_signal10` | annexb | `annexb_sig10/*` + xlsx | mosqito N(t)；ISO 時間軸；ISO N(t) | 1e-6/1e-9；1e-12；isoclose | 12 |
| `loudness_zwtv_rejects_unsupported_sample_rate` | api_errors | `44100.0` | `Err(UnsupportedSampleRate)` | 精確 | 12 |
| `loudness_zwtv_rejects_short_signal` | api_errors | `[0.0; 4799]` | `Err(SignalTooShort)` | 精確 | 12 |

## 4. 已知差異風險 / 排查順序

**`nl_loudness` 三個已知差異點（主計畫 Task 11，失敗時照順序處置；`pulse_1k_70` 與 `step_60_80` 最能暴露）：**

1. **初始狀態的 mosqito 環繞行為**：`uo_last = core[last]/24`（取最後一 frame 除以 24，非 0）。
2. **比較運算子等號方向**：衰減/攻擊分支的 `>` vs `>=`、`<` vs `<=` 須與 mosqito 逐一對齊。
3. **uo 衰減 mask 不含 `ui < uo_last` 檢查**：mosqito 的 mask 組合順序特殊，勿自行「補上」看似合理的條件。

**其他：**

4. **scalar 最終語意必須註解**：若為復刻 mosqito 而改動 scalar 分支，**必須在程式碼註解記錄最終語意**——Phase 4 AVX kernel 照 scalar 最終版寫（見 [phase-4](phase-4-avx2.md) §4）。
5. **時間軸語意**：`time_axis` 改用固定樣本網格（非累加）後才能對 ISO xlsx 達 `1e-12`；`third_octave_levels` 的 2 kHz 抽樣（`[::4]` 對應 `DEC_FACTOR`）要與 mosqito 一致。
6. **xlsx 參考轉換**：先用 openpyxl 印 sheet 結構、對照 mosqito `test_loudness_zwtv.py` 的讀法再實作 `tv_time.bin`/`tv_nref.bin`。

## 5. 驗收對照

```bash
cd iso532
cargo test --test golden_zwtv    # third_octave_levels/nl_loudness/temporal_weighting/E2E
cargo test --test annexb         # 含 signal 10 時變三重驗證
cargo test --test api_errors     # zwtv 錯誤路徑
cargo test                       # 全綠
cargo clippy -- -D warnings      # 乾淨
```

前置：Phase 2 完成（`core/` 與 golden 基礎設施就緒）。詳見 [plans/phase-3](../plans/phases/phase-3-zwtv-scalar.md)。
