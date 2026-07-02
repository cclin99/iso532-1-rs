# ISO 532-1 (Zwicker Loudness) Rust + AVX 改寫設計

日期：2026-07-03
來源基準：mosqito 1.2.1（`D:\ISO532\mosqito-1.2.1`，由 tarball 解壓，不入 git）

## 目標

將 mosqito 1.2.1 的 ISO 532-1:2017 響度實作（穩態 `loudness_zwst` + 時變 `loudness_zwtv`）改寫為純 Rust crate，並對計算熱點提供 AVX2+FMA 加速（runtime 偵測、scalar fallback）。

## 已確認決策

| 決策 | 結論 |
|---|---|
| 範圍 | 穩態 zwst + 時變 zwtv 兩者 |
| 交付形式 | 純 Rust crate（lib）+ CLI 範例 |
| SIMD | AVX2 + FMA intrinsics（`std::arch`），runtime 偵測，scalar fallback |
| 驗證 | 兩層：mosqito 逐階段 golden 比對 + ISO 532-1 Annex B 官方測試訊號 |
| 演算法結構 | 分階段：先照 ISO C 參考程式的逐 frame 邏輯寫正確的 scalar 版，驗證通過後再加 AVX2 kernel |
| 精度 | f64 全程（匹配 mosqito） |

## 現況分析（mosqito 1.2.1）

### 穩態 pipeline（loudness_zwst）

1. `noct_spectrum`：28 頻帶 1/3 倍頻程 Butterworth 3 階帶通（ANSI S1.1 設計、SOS 形式、`scipy.signal.butter` 雙線性轉換）；`fc < fs/200` 的低頻帶先以 `scipy.signal.decimate`（Cheby1 8 階 + filtfilt 零相位）降採樣；每帶取 RMS。熱點：28 × 訊號長度 IIR。
2. `amp2db`：20·log10(rms/2e-5)。
3. `_main_loudness`：28 頻帶 → 20 臨界頻帶核心響度。低頻等響曲線修正（rap/dll 表 8×11）、前三臨界頻帶能量合併（lcb）、耳傳輸修正 a0、擴散場修正 ddf、閾值 ltq、dcb 修正、`0.0635·10^(0.025·ltq)·((1-s+s·10^((le-ltq)/10))^0.25 − 1)`、第一頻帶 korry 修正。低頻 11 帶超過 120 dB → 錯誤。
4. `_calc_slopes`：上行遮蔽斜率（zup/rns/usl 表）+ 0.1 Bark 步進積分 → 總響度 N 與 240 點 N_specific；尾端量化（N≤16 取 0.001、N>16 取 0.01）。

### 時變 pipeline（loudness_zwtv）

1. `_third_octave_levels`：ISO Table A.1/A.2 固定係數 28 頻帶 × 3 級 biquad 串接 @48 kHz；平方；3 級一階平滑（τ = 2/(3·min(fc,1000))）；降採樣至 2 kHz；dB（+1e-12 底噪、ref 4e-10）。**最大熱點（~9 成計算量）**。
2. `_main_loudness`：同穩態，跨所有 2 kHz frames。
3. `_nl_loudness`：非線性時間衰減。24× 線性內插虛擬升採樣（48 kHz 有效率）、雙電容類比模型（τ_short=5ms、τ_long=15ms、τ_var=75ms，B[0..5] 常數）、5 組條件分支的時間遞迴。時間軸循序、跨 21 頻帶可平行。**第二熱點**。
4. `_calc_slopes`：同穩態，逐 frame。
5. `_temporal_weighting`：0.47·LP(τ=3.5ms) + 0.53·LP(τ=70ms)，各為 24× 線性內插一階濾波。
6. 抽樣 ×4 → 2 ms 輸出解析度。

### 對改寫重要的觀察

- Python 版的跨時間 mask 向量化（`_calc_slopes`、`_nl_loudness`）是遷就 numpy 的扭曲寫法（含 `round(x, 8)` 補丁），不作為 Rust 藍本；Rust 回歸 ISO C 參考程式的逐 frame 結構。
- IIR 在時間軸有遞迴相依，SIMD 的正確平行軸是「跨頻帶」：28 頻帶 = 7 個 f64×4 AVX2 向量。
- sdist 未附測試資料；ISO Annex B 測試 wav 與參考 csv/xlsx 需自 MoSQITo GitHub repo `tests/input/` 下載。
- 需在 Rust 重現的 scipy 元件：`sosfilt`、`sosfiltfilt`（含 odd padding 與 steady-state 初值）、`lfilter`（一階）。濾波器「設計」（`butter`、`cheby1`）不在 Rust 重現：因 fs 固定 48 kHz，所有 zwst 濾波器係數由 `tools/gen_tables.py` 以 scipy 生成後烘焙為 Rust 常數，與 scipy 位元級一致。

## Crate 架構

```
iso532/
├── Cargo.toml            # crate name: iso532
├── src/
│   ├── lib.rs            # 公開 API
│   ├── error.rs          # thiserror 錯誤型別
│   ├── tables.rs         # 全部 ISO 常數表（A.1/A.2 係數、rap/dll/ltq/a0/ddf/dcb/zup/rns/usl、filter_gain）
│   ├── tables_noct.rs    # tools/gen_tables.py 以 scipy 生成：zwst 28 頻帶 Butterworth SOS
│   │                     #   + Cheby1 降採樣 SOS（fs 固定 48 kHz，故全為常數；
│   │                     #   免除在 Rust 重現 scipy 濾波器設計/零極點配對的數值風險）
│   ├── dsp/
│   │   ├── sos.rs        # SOS biquad 串接濾波 + 一階低通（scalar + avx2）
│   │   └── filtfilt.rs   # sosfiltfilt（odd padding）+ decimate
│   ├── core/
│   │   ├── main_loudness.rs   # 逐 frame scalar
│   │   └── calc_slopes.rs     # 逐 frame scalar（照 ISO C 參考邏輯）
│   ├── zwst/mod.rs       # noct_spectrum + 穩態流程
│   ├── zwtv/
│   │   ├── mod.rs
│   │   ├── third_octave_levels.rs  # scalar + avx2
│   │   ├── nonlinear_decay.rs      # scalar + avx2
│   │   └── temporal_weighting.rs
│   └── simd/
│       ├── dispatch.rs   # is_x86_feature_detected!("avx2") && ("fma")
│       └── f64x4.rs      # std::arch 薄封裝
├── examples/cli.rs       # 讀 WAV → N / N_specific
├── tests/                # golden 逐階段比對 + ISO Annex B 驗證
├── tools/gen_golden.py   # mosqito 1.2.1 逐階段參考輸出產生器
├── benches/              # criterion：scalar vs AVX2
└── data/                 # golden 資料 + Annex B 測試訊號（下載）
```

## 公開 API

```rust
pub enum FieldType { Free, Diffuse }

pub struct LoudnessStationary {
    pub n: f64,                 // sone
    pub n_specific: Vec<f64>,   // 240 點 (0.1..24 Bark)
    pub bark_axis: Vec<f64>,
}

pub struct LoudnessTimeVarying {
    pub n: Vec<f64>,            // sone / frame (2 ms)
    pub n_specific: Vec<f64>,   // 扁平 row-major：240 列 × frames 行，索引 [bark_idx * frames + t]
    pub bark_axis: Vec<f64>,
    pub time_axis: Vec<f64>,
}

pub fn loudness_zwst(signal: &[f64], fs: f64, field: FieldType)
    -> Result<LoudnessStationary, Iso532Error>;
pub fn loudness_zwtv(signal: &[f64], fs: f64, field: FieldType)
    -> Result<LoudnessTimeVarying, Iso532Error>;
```

## AVX2 加速策略（第二階段）

| 模組 | 策略 | 預期效益 |
|---|---|---|
| `third_octave_levels` 濾波器組 | band-major SoA，f64×4 × 7 向量逐樣本推進，biquad + 平方 + 平滑全 FMA | 主要收益 ~3-4× |
| `nl_loudness` | 跨 21 臨界頻帶 SIMD（6 向量），分支改 compare+blend | 次要收益 |
| `main_loudness` | 逐元素冪運算向量化；log10/10^x 走 per-lane libm 保精度 | 小 |
| `calc_slopes` | 不做 SIMD（分支發散），維持逐 frame scalar | — |
| zwst `noct_spectrum` | 共用 SOS AVX kernel，28 頻帶並行 | 中 |

Runtime 偵測 AVX2+FMA，無則走 scalar；AVX 與 scalar 版共用同一組測試互驗（容差 ~1 ulp 級，允許 FMA 造成的最後位差異）。

## 驗證計畫（兩層）

1. **逐階段 golden 比對**：`tools/gen_golden.py` 以 mosqito 1.2.1（Python venv）對測試訊號組（250/1000/4000 Hz 正弦 × 40/60/80 dB、粉紅噪音、1 kHz 音調脈衝、掃頻）輸出每階段中間結果（zwst：spec_third dB、Nm、N、N_specific；zwtv：third_octave_level、core_loudness、nl_loudness、N(t)、N_specific(t)）為 CSV/二進位。Rust 整合測試逐階段比對：結構相同處容差 1e-9，運算順序不同處（濾波累加、冪運算鏈）放寬至 1e-6 相對誤差。
2. **ISO 532-1 Annex B 官方測試**：自 MoSQITo GitHub `tests/input/` 下載測試 wav 與參考值（csv/xlsx），依 mosqito 測試同基準驗證（穩態：N_specific 容差帶 ±5%/±0.1 sone 型判準；時變：xlsx 參考曲線容差帶）。

## 邊界與錯誤處理

- 低頻 11 帶（25–250 Hz）任一 >120 dB → `Err(Iso532Error::LevelExceeds120dB)`。
- **輸入一律要求 fs = 48000 Hz**；不內建重採樣（mosqito 的 scipy FFT resample 屬前處理），文件註明由呼叫端處理，CLI 範例遇非 48 kHz 直接報錯。
- 空訊號 / 過短訊號 → `Err(Iso532Error::SignalTooShort)`。

## Non-goals（本期不做，架構預留）

- f32 快速模式
- rayon 多執行緒
- `loudness_zwst_freq` / `loudness_zwst_perseg` 變體
- Python binding（pyo3）、C FFI
- 取樣率轉換

## 里程碑

1. **骨架與資料**：crate 建立、`tables.rs` 常數移植、Python venv + `gen_golden.py`、下載 Annex B 測試資料。
2. **zwst scalar**：butter/sosfilt/decimate → noct_spectrum → main_loudness → calc_slopes，逐階段過 golden。
3. **zwtv scalar**：third_octave_levels → nl_loudness → temporal_weighting，逐階段過 golden。
4. **ISO Annex B 驗收**：兩條 pipeline 過官方測試訊號。
5. **AVX2 第一波**：SOS 濾波器組 kernel + runtime dispatch + scalar 互驗 + criterion 基準。
6. **AVX2 第二波**：nl_loudness、main_loudness 向量化 + 基準報告。
7. **收尾**：rustdoc、CLI 範例、README（含加速比數據）。
