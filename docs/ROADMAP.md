# ISO532 專案 Roadmap

目前工作：`iso532` crate（ISO 532-1 Zwicker 響度，Rust + AVX2）——spec 與分階段計畫見 `docs/superpowers/`。

以下為後續方向（2026-07-03 記錄）。**均不在目前 5 個 phase 的範圍內**，但列出對現行實作的架構影響，避免之後重工。

## 1. 延伸到其他心理聲學標準

候選：ECMA-418-2（Sottek hearing model 響度/音調性）、ISO 532-2（Moore-Glasberg）、sharpness（DIN 45692）、roughness、fluctuation strength。mosqito 同倉庫有 ECMA 與 sharpness 參考實作可沿用同一套 golden 驗證方法。

**對現行實作的要求：**
- `dsp/`（sosfilt、filtfilt、onepole、SIMD filter bank kernel）保持與 ISO 532-1 業務邏輯解耦，之後可直接複用。
- workspace 化預留：之後改為 cargo workspace（`dsp-core` / `iso532-1` / `ecma418` ...），目前單 crate 即可，但模組邊界要乾淨。
- sharpness 可直接吃 `LoudnessStationary/TimeVarying` 的 `n_specific`——輸出結構已含完整 240 點 specific loudness，夠用。

## 2. 64 軌 VST 插件（即時響度量測）

**對現行實作的要求（影響最大）：**
- **串流 API**：目前 API 是整段訊號批次計算。即時 VST 需要 chunk-by-chunk 處理與持續濾波器狀態。現行 kernel 內部本來就是逐樣本推進 + 顯式狀態（biquad z0/z1、平滑、nl uo/u2），之後抽出 `struct LoudnessStream { push(&mut self, chunk: &[f64]) -> ... }` 是重構而非重寫——**實作時避免把狀態埋死在函式區域變數以外的全域**（目前計畫已符合）。
- **效能目標**：64 軌 × 48 kHz 即時 = 每秒處理 3.07M 樣本；zwtv 熱點約 28 頻帶 × 6 IIR/樣本。Phase 5 的 benchmark 結果要對照這個目標評估（單軌 10 s 訊號應遠快於 10 s wall-clock；64 軌可跨軌 rayon 平行——每軌一 thread 天然平行，屆時再加）。
- 注意 zwst 的 `sosfiltfilt`（零相位、需完整訊號）**無法串流**——即時場景只用 zwtv 路徑，不是問題。
- VST 框架屆時評估（nih-plug 為主要候選）。

## 3. dB SPL 與 Sone 顯示面板

- 引擎輸出已含所需資料：`third_octave_levels`（dB SPL/頻帶）、`N(t)`（sone）、`N_specific`（sone/Bark）。
- 需要補的是 phon 轉換（`sone2phone`：N ≥ 1 → 40 + 10·log2(N)，mosqito utils 有參考）——很小，屆時加進 crate。
- 面板本體屬 VST/GUI 工作，引擎側只需保證：輸出結構可增量取得（串流 API 一併解決）。

## 4. C-ABI 與 Python 對接

- **C-ABI**：獨立 `iso532-ffi` crate（`cdylib` + `#[no_mangle] extern "C"`），扁平 f64 陣列 + 長度參數。現行輸出已刻意用扁平 row-major `Vec<f64>`（`n_specific` 為 `bark_idx * n_frames + frame`），就是為此鋪路——**不要改成巢狀 Vec**。
- **Python**：pyo3 + maturin，回傳 numpy array；驗證直接複用 golden（Python 端跑 mosqito 與 Rust binding 互比）。
- 錯誤處理：`Iso532Error` 已是可枚舉的具名錯誤，FFI 映射為錯誤碼即可。

## 5. 跨平台：Linux (Ubuntu) 與 Apple M 系列

**現行計畫已可直接編譯執行於兩個平台**，不需改動：

- 純 Rust + 純 Rust 依賴（thiserror、hound、criterion），無平台專屬系統呼叫。
- AVX2 kernel 與 dispatch 呼叫點都在 `#[cfg(target_arch = "x86_64")]` 之內；`avx2_available()` 在非 x86_64 編譯期回 `false`。aarch64（Apple M）上整個 AVX 模組不參與編譯，自動走 scalar 路徑。
- golden `.bin` 為 f64 little-endian——x86-64 與 Apple M（aarch64）皆為 LE，測試資料跨平台共用。
- 工具鏈腳本（`setup_env.sh`、`gen_golden.py`、`gen_tables.py`）為 bash/Python，Linux/macOS 原生可跑。
- 後續 C-ABI（cdylib）與 VST（nih-plug 支援 Win/macOS/Linux）在三平台皆成立。

**各平台狀態：**

| 平台 | 編譯/正確性 | SIMD 加速 |
|---|---|---|
| Windows / Linux x86-64 | ✅ | AVX2+FMA（runtime 偵測） |
| Linux aarch64、Apple M 系列 | ✅（scalar） | 待補 NEON kernel（見下） |

**Apple M 系列 NEON kernel（未來工作，非現行 5 phases 範圍）：**

- NEON 是 128-bit：`f64x2`，28 頻帶 = 14 個向量（vs AVX2 的 7 個）；FMA 用 `vfmaq_f64`，分支消除用 `vmaxq_f64`/`vminq_f64`/`vbslq_f64`，與 AVX2 kernel 一一對應，移植是機械性工作。
- aarch64 上 NEON 是 baseline feature——**不需 runtime 偵測**，`#[cfg(target_arch = "aarch64")]` 直接編入即可，dispatch 比 x86 端更簡單。
- 前置條件：Phase 4 的 AVX2 kernel 定案後照抄結構；`simd_parity` 測試同樣直接複用（scalar vs NEON）。
- 注意：`simd_parity` 在無 AVX2 的機器上會 skip——在 M 系列機器上跑 `cargo test` 全綠只代表 scalar 正確，不代表驗過 SIMD。

**CI 建議（屆時）：** GitHub Actions 三 job——`windows-latest`、`ubuntu-latest`（x86-64，驗 AVX2 路徑）、`macos-latest`（M 系列 runner，驗 aarch64 scalar/NEON）。

## 執行順序建議

1. 現行 5 phases（Codex 實作）
2. C-ABI + Python binding（驗證便利、立即可用）
3. 串流 API 重構 + phon 轉換
4. VST 插件（64 軌 + 面板）
5. 其他標準（workspace 化後逐一加）
