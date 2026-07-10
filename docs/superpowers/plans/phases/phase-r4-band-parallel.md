# Phase R4: filter_bank / nl_loudness 頻帶平行化(離線吞吐)Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把多執行緒下僅存的兩個序列階段平行化——`third_octave_levels`(19.6 ms,佔 MT 時間 ~28%)與 `nl_loudness`(17.4 ms,~25%)按頻帶群組分派 rayon,多執行緒 `zwtv_10s` 自 69.3 ms 降至 45–55 ms 區間,輸出**逐位不變**。

**Architecture:** 兩階段的時間遞迴都只存在於帶內、跨帶零依賴。band-major 佈局(`out[band*n_time+t]`)下,4 帶群組正好是輸出的**連續切片**,`par_chunks_mut(4*n_time)` 天然滿足「每工作項寫互斥槽位」不變式。tol 的 AVX2 kernel 需先做迴圈互換(現為 t 外層、群組內層 → 抽出「單群組完整掃訊號」kernel);nl 的 AVX2 已是群組外層,只需把寫入目標改為群組切片。平行入口統一收 `ParMode { Rayon, Sequential }`,為 R5 串流路徑(音訊執行緒不得觸發 thread pool)預留 Sequential。

**Tech Stack:** Rust 2021、rayon 1.12(par_chunks_mut,既有依賴)、std::arch AVX2/FMA、criterion、FNV-1a 雜湊快照(R1 建立)。

**來源:** `docs/superpowers/plans/2026-07-05-roadmap-master-plan.md` R4 節(範圍、驗收、風險以該文件為準)。

---

## 前置條件(執行前確認,缺一不動工)

1. `data/golden/` 存在且含 `sine_1k_60`、`pulse_1k_70`、`step_60_80`、`white_60`、`annexb_sig10` 等訊號目錄(gitignored;缺失時以 `tools/gen_golden.py` 重生,需 Python venv + mosqito==1.2.1)。
2. `cargo test -p iso532` 目前全綠(乾淨基線)。
3. 本機為 AVX2 機器(基準對照 Ryzen 5 3600;非此機器時效能驗收只看相對變化)。
4. **bench 時機器必須閒置**(R1 教訓:背景負載曾造成多執行緒 scalar +3% 假性劣化)。

## 驗收準則(逐字複製自主計畫 R4,不得改寫)

1. golden 逐位不變(頻帶獨立 ⇒ 平行化不得改變任何位元;若變即為實作錯誤,不是可接受誤差)。
2. simd_parity 不變。
3. criterion:多執行緒 zwtv_10s 自 ~79 ms 降至 45–55 ms 區間(推估需實測修正);**單執行緒不得劣化 >2%**。
4. 決定性測試:同輸入跑 20 次,輸出逐位相同。

> **操作化備註:**
> - 準則 1 的實際看守 = `dump_zwtv_output_hashes`(R1 建立)對照 **R1 已記錄的 12 個參考雜湊**(見 Task 0),每個行為變更 commit 後逐字比對,不需重新取基線。
> - 準則 3 的「~79 ms」為主計畫撰寫時基線;R1 落地後實測基線為 **69.3 ms(MT AVX2)/ 244.7 ms(ST AVX2)**,45–55 ms 目標區間不變。單執行緒 >2% 劣化以 244.7 ms(AVX2)與 535.5 ms(scalar)為對照。
> - 準則 4 由 Task 1 的新測試 `tests/determinism.rs` 落實(先於任何平行化落地)。

## 已知風險(主計畫 4 項 + 本計畫探索新增 5 項)

| # | 風險 | 緩解(本計畫落點) |
|---|---|---|
| 1 | 7 群組同時全速掃 3.84 MB 訊號 → L3 頻寬競爭,加速遠低於 7× | 預期管理:收益 <2× 則記錄實測回報並依主計畫討論群組配對(4 工),**不阻擋合入** |
| 2 | 輸出跨步寫入 false sharing | band-major 下每群組寫**連續**切片(`par_chunks_mut`),僅切片邊界一條 cache line 可能共享,無需額外處理 |
| 3 | rayon 巢狀死鎖疑慮 | `process()` 內三個 par 點嚴格先後執行、無巢狀;R5 串流以 `ParMode::Sequential` 型別強制 |
| 4 | 群組間 filter 狀態誤共享 | 狀態全部是 kernel 函式區域變數(Task 2 抽 kernel 時自然隔離),編譯期即不可共享 |
| 5 | **`chunks_mut(0)` panic**:`n_time == 0`(空訊號)時 chunk 尺寸為 0 會 panic;現行 tol 兩路徑容忍空輸入 | tol 兩路徑補 `n_time == 0` early return(nl 的 avx2 已有守衛、scalar 需補) |
| 6 | **`#[target_feature]` × rayon closure**:closure 繼承 target_feature 進 rayon 泛型機制屬脆弱地帶 | 重構後 `_avx2` 入口函式不再含 intrinsics → **移除其 `#[target_feature]`**(保留 `unsafe fn` + safety doc);僅 per-group kernel 保留屬性;closure 內以 `unsafe {}` + SAFETY 註解呼叫 kernel |
| 7 | scalar 平行的暫態記憶體 = min(緒數, 帶數) × 每帶配置(10s 訊號 @12 緒:tol ~46 MB、nl ~138 MB),隨訊號長度線性放大 | 離線批次限定(文件註明);`RAYON_NUM_THREADS` 可壓;R5 scratch 化(R1 遺留 #1)根治 |
| 8 | `FORCE_SCALAR` 行程級全域 vs 測試多緒 race | determinism 測試獨立成 `tests/determinism.rs` 且**全檔僅一個 `#[test]`**(整合測試每檔一個行程,單測試 = 無並發) |
| 9 | Sequential 臂 bit-rot(平常只有 Rayon 臂被 e2e 走到) | simd_parity 走 Sequential、golden e2e/determinism 走 Rayon、determinism 內的**模式逐位等價斷言**綁死兩臂——同時是 R5「串流 Sequential == 批次 Rayon」的前置契約 |

## 範圍外(明確不做,防 scope creep)

- nl 輸出改 time-major(R1 遺留 #2):頻帶平行的互斥 chunk 正依賴 band-major 連續性,兩者方向衝突;評估結論為**不併入**。
- nl / temporal_weighting 每呼叫配置移除(R1 遺留 #1):R5 零配置驗收的工作。
- `zwtv/mod.rs` 的 DEC_FACTOR 抽常數(R1 遺留 #3)、R1 融合迴圈的 `with_min_len`(R1 遺留 #4):不同檔案。

---

### Task 0: 基線確認(無 commit)

- [ ] **Step 1: 全量測試綠**

Run: `cargo test -p iso532`
Expected: 全綠。

- [ ] **Step 2: 雜湊基線對照 R1 紀錄**

Run: `cargo test -p iso532 --test golden_zwtv dump_zwtv_output_hashes -- --ignored --nocapture`
Expected: 4 行輸出與 R1 記錄的參考雜湊**逐字相同**(否則基線已髒,停工回報):

```
sine_1k_60: n=0b10971021634b4e spec=62496b610f7c223d time=f076bcb342595537
pulse_1k_70: n=b92a2b970de3067f spec=bdab430b961720f0 time=f076bcb342595537
step_60_80: n=40ac75b0dcaed5a8 spec=2fdc839b4f702621 time=f076bcb342595537
annexb_sig10: n=83da1e1c06d5296c spec=3c2b914686402b54 time=f076bcb342595537
```

- [ ] **Step 3: bench 基線(機器閒置)**

Run(多執行緒): `cargo bench -p iso532 --bench loudness -- zwtv_10s`
Run(單執行緒): `RAYON_NUM_THREADS=1 cargo bench -p iso532 --bench loudness -- zwtv_10s`
Run(filter bank,多+單): `cargo bench -p iso532 --bench loudness -- filter_bank_10s` 與 `RAYON_NUM_THREADS=1` 版
Expected: zwtv_10s avx2 參考值 MT ~69.3 ms、ST ~244.7 ms(±機器噪音)。**記下全部八個數字**(zwtv/filter_bank × scalar/avx2 × MT/ST),Task 3/5/6 要做 A/B。filter_bank_10s 尚無歷史紀錄,本次即建立。

---

### Task 1: 決定性看守測試(先於任何行為變更)

**Files:**
- Modify: `iso532/tests/common/mod.rs`(檔尾追加)
- Modify: `iso532/tests/golden_zwtv.rs`(刪除檔尾私有 `fnv1a_f64`,改用 common 版)
- Create: `iso532/tests/determinism.rs`

- [ ] **Step 1: `fnv1a_f64` 搬入 common**

在 `tests/common/mod.rs` 檔尾追加(與既有 `assert_close` 同款 `#[allow(dead_code)]`,因各測試 binary 獨立編譯 common):

```rust
#[allow(dead_code)]
pub fn fnv1a_f64(values: &[f64]) -> u64 {
    let mut hash = 0xcbf2_9ce4_8422_2325_u64;
    for value in values {
        for byte in value.to_le_bytes() {
            hash ^= u64::from(byte);
            hash = hash.wrapping_mul(0x0000_0100_0000_01b3);
        }
    }
    hash
}
```

刪除 `tests/golden_zwtv.rs` 檔尾的整個 `fn fnv1a_f64`(第 79–88 行);該檔已 `use common::*;`,`dump_zwtv_output_hashes` 不需其他改動。

- [ ] **Step 2: 新增 `tests/determinism.rs`**

完整檔案內容:

```rust
#[allow(dead_code)]
mod common;

use iso532::{loudness_zwtv, simd, FieldType};

const FS: f64 = 48_000.0;

/// 與 benches/loudness.rs 的 bench_signal 同配方,1 秒長(高於 4800 樣本下限),
/// 不依賴 data/golden,任何環境都能跑。
fn synth_signal() -> Vec<f64> {
    (0..48_000)
        .map(|i| {
            let t = i as f64 / FS;
            0.25 * (2.0 * std::f64::consts::PI * 440.0 * t).sin()
                + 0.10 * (2.0 * std::f64::consts::PI * 1_760.0 * t).sin()
                + 0.04 * (2.0 * std::f64::consts::PI * 6_400.0 * t).sin()
        })
        .collect()
}

fn run_hashes(signal: &[f64]) -> (u64, u64, u64) {
    let r = loudness_zwtv(signal, FS, FieldType::Free).unwrap();
    (
        common::fnv1a_f64(&r.n),
        common::fnv1a_f64(&r.n_specific),
        common::fnv1a_f64(&r.time_axis),
    )
}

fn assert_20_runs_identical(signal: &[f64], ctx: &str) {
    let first = run_hashes(signal);
    for run in 1..20 {
        assert_eq!(run_hashes(signal), first, "{ctx}: run {run} diverged");
    }
}

// FORCE_SCALAR 是行程級全域;整合測試每檔一個行程、檔內測試多緒併發,
// 因此本檔**只允許存在這一個 #[test]**——切換旗標才無 race。
#[test]
fn zwtv_output_is_bitwise_deterministic_over_20_runs() {
    let signal = synth_signal();

    assert_20_runs_identical(&signal, "auto dispatch");

    simd::set_force_scalar(true);
    assert_20_runs_identical(&signal, "forced scalar");
    simd::set_force_scalar(false);
}
```

- [ ] **Step 3: 執行,預期直接通過(現行程式碼已是決定性)**

Run: `cargo test -p iso532 --test determinism`
Expected: PASS(1 test)。
Run: `cargo test -p iso532 --test golden_zwtv`
Expected: 全綠(fnv 搬遷是純搬移)。

- [ ] **Step 4: Commit**

```bash
git add iso532/tests/common/mod.rs iso532/tests/golden_zwtv.rs iso532/tests/determinism.rs
git commit -m "test: add 20-run bitwise determinism guard for zwtv output"
```

---

### Task 2: tol AVX2 迴圈互換——抽 per-group kernel,序列呼叫(本階段最高風險步)

**Files:**
- Modify: `iso532/src/zwtv/third_octave_levels.rs`(第 58–146 行整段替換)

**逐位不變論證(實作前先讀懂):** 現行 t 外層 kernel 中,群組 `v` 在樣本 `i` 的更新只讀群組 `v` 自己的狀態(`z0/z1/sm[..][v]`)、群組 `v` 的係數、與廣播樣本值。迴圈互換(改為群組外層、各自完整掃訊號)後,**每個群組的浮點指令序列完全不變**;寫入位址 `out[(4v+lane)*n_time+frame]` 亦不變(群組切片起點即 `4v*n_time`)。唯一移動的是 `frame` 計數器進 kernel 內——遞增條件 `i % DEC_FACTOR == 0` 等價。因此輸出必然逐位相同;Step 3 雜湊比對即為看守。

- [ ] **Step 1: 以 per-group kernel + 序列 chunks_mut 取代現行 `third_octave_levels_avx2`**

將第 58–146 行(自 `/// AVX2+FMA filter bank kernel...` 起、至該函式結尾 `}` 止)整段替換為:

```rust
/// 單一 f64x4 群組(帶 4v..4v+4)完整掃訊號的 AVX2+FMA kernel。
///
/// # Safety
/// Caller must ensure AVX2 and FMA are available before calling.
#[cfg(target_arch = "x86_64")]
#[target_feature(enable = "avx2,fma")]
unsafe fn tol_group_avx2(sig: &[f64], v: usize, out_group: &mut [f64], n_time: usize) {
    use std::arch::x86_64::*;

    debug_assert_eq!(out_group.len(), 4 * n_time);

    let mut g = [0.0; 4];
    let mut b0s = [0.0; 4];
    let mut a1s = [0.0; 4];
    let mut a1c = [[0.0; 4]; 3];
    let mut a2c = [[0.0; 4]; 3];
    for lane in 0..4 {
        let band = 4 * v + lane;
        g[lane] = TOB_GAIN[band];
        let (b0, smooth_a1) = smoothing_coeff(band);
        b0s[lane] = b0;
        a1s[lane] = smooth_a1;
        for section in 0..3 {
            a1c[section][lane] = -2.0 - TOB_DELTA[band][section][0];
            a2c[section][lane] = 1.0 - TOB_DELTA[band][section][1];
        }
    }
    let gain = _mm256_loadu_pd(g.as_ptr());
    let sb0 = _mm256_loadu_pd(b0s.as_ptr());
    let sa1 = _mm256_loadu_pd(a1s.as_ptr());
    let mut a1 = [_mm256_setzero_pd(); 3];
    let mut a2 = [_mm256_setzero_pd(); 3];
    for section in 0..3 {
        a1[section] = _mm256_loadu_pd(a1c[section].as_ptr());
        a2[section] = _mm256_loadu_pd(a2c[section].as_ptr());
    }

    let b1s = [2.0, 0.0, -2.0];
    let b2s = [1.0, -1.0, 1.0];
    let mut z0 = [_mm256_setzero_pd(); 3];
    let mut z1 = [_mm256_setzero_pd(); 3];
    let mut sm = [_mm256_setzero_pd(); 3];

    let mut frame = 0usize;
    for (i, &sample) in sig.iter().enumerate() {
        let xs = _mm256_set1_pd(sample);
        let mut y = _mm256_mul_pd(xs, gain);
        for section in 0..3 {
            let xin = y;
            y = _mm256_add_pd(xin, z0[section]);
            let b1v = _mm256_set1_pd(b1s[section]);
            let t = _mm256_fmadd_pd(b1v, xin, z1[section]);
            z0[section] = _mm256_fnmadd_pd(a1[section], y, t);
            let b2v = _mm256_set1_pd(b2s[section]);
            z1[section] = _mm256_fnmadd_pd(a2[section], y, _mm256_mul_pd(b2v, xin));
        }

        y = _mm256_mul_pd(y, y);
        for stage_state in &mut sm {
            *stage_state = _mm256_fmadd_pd(sb0, y, _mm256_mul_pd(sa1, *stage_state));
            y = *stage_state;
        }

        if i % DEC_FACTOR == 0 {
            let mut lanes = [0.0; 4];
            _mm256_storeu_pd(lanes.as_mut_ptr(), y);
            for lane in 0..4 {
                out_group[lane * n_time + frame] = 10.0 * ((lanes[lane] + TINY) / I_REF).log10();
            }
            frame += 1;
        }
    }
}

/// AVX2+FMA filter bank:28 帶 = 7 個 f64x4 群組,每群組獨立完整掃訊號。
///
/// 本函式已無 intrinsics(僅切 chunk 與呼叫 kernel),故不標 `#[target_feature]`
/// ——closure 繼承 target_feature 進 rayon 泛型屬脆弱地帶(見 phase 計畫風險 #6)。
///
/// # Safety
/// Caller must ensure AVX2 and FMA are available before calling.
#[cfg(target_arch = "x86_64")]
pub unsafe fn third_octave_levels_avx2(sig: &[f64]) -> (Vec<f64>, usize) {
    let n_time = sig.len().div_ceil(DEC_FACTOR);
    let mut out = vec![0.0; N_TOB_BANDS * n_time];
    if n_time == 0 {
        return (out, 0);
    }
    for (v, group) in out.chunks_mut(4 * n_time).enumerate() {
        tol_group_avx2(sig, v, group, n_time);
    }
    (out, n_time)
}
```

設計要點(不可偏離):
- kernel 內每群組只做**自己 4 帶**的係數設定(現行 77–101 行對所有 NV 群組設定的迴圈,取單一 `v` 切片),數值來源同表、逐位相同。
- 狀態陣列降維:`[[__m256d; NV]; 3]` → `[__m256d; 3]`(函式區域,編譯期隔離——主計畫風險 #4 的緩解)。
- 28 = 7×4 整除,`chunks_mut(4 * n_time)` 每個 chunk 都是完整群組,無尾差。
- `n_time == 0` 守衛必加(風險 #5:`chunks_mut(0)` panic;現行程式碼容忍空輸入)。

- [ ] **Step 2: 全量測試**

Run: `cargo test -p iso532`
Expected: 全綠(simd_parity 的 `filter_bank_avx2_matches_scalar` 此處實際上是逐位相同,容差 1e-10 必過)。

- [ ] **Step 3: 雜湊比對(逐字對 Task 0 Step 2 的 12 值)**

Run: `cargo test -p iso532 --test golden_zwtv dump_zwtv_output_hashes -- --ignored --nocapture`
Expected: 12/12 逐字相同。**任一不同即為迴圈互換寫錯(frame 計數或群組切片位移),回退 Step 1 重查,不得放寬。**

- [ ] **Step 4: Commit**

```bash
git add iso532/src/zwtv/third_octave_levels.rs
git commit -m "refactor: extract per-group tol avx2 kernel, group-outer sequential scan"
```

---

### Task 3: ParMode 導入 + tol 平行化(AVX2 7 工 + scalar 28 工)

**Files:**
- Modify: `iso532/src/zwtv/mod.rs`(新增 `ParMode`)
- Modify: `iso532/src/zwtv/third_octave_levels.rs`(平行臂 + 四層入口)
- Modify: `iso532/tests/simd_parity.rs`(`_avx2` 呼叫補 mode 參數)
- Modify: `iso532/tests/determinism.rs`(補 tol 模式等價斷言)

- [ ] **Step 1: `zwtv/mod.rs` 新增 ParMode**

在 `use rayon::prelude::*;`(第 9 行)之後、`ZwtvProcessor` 定義之前插入:

```rust
/// 頻帶平行階段的排程模式。離線批次走 `Rayon`;
/// R5 串流路徑必須選 `Sequential`(音訊路徑不得觸發 thread pool)。
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ParMode {
    Rayon,
    Sequential,
}
```

- [ ] **Step 2: tol 四層入口 + 平行臂**

`third_octave_levels.rs` 檔頭 imports 補:

```rust
use super::ParMode;
use rayon::prelude::*;
```

(a) 現行 `third_octave_levels_scalar`(第 33–56 行)拆為 per-band helper + `_impl`,公開函式簽名不變:

```rust
fn tol_band_scalar(sig: &[f64], band: usize, out_row: &mut [f64]) {
    let mut x: Vec<f64> = sig.iter().map(|v| v * TOB_GAIN[band]).collect();
    sosfilt(&band_sos(band), &mut x);

    for v in &mut x {
        *v *= *v;
    }

    let (b0, a1) = smoothing_coeff(band);
    for _ in 0..3 {
        onepole(b0, a1, &mut x);
    }

    for (t, v) in x.iter().step_by(DEC_FACTOR).enumerate() {
        out_row[t] = 10.0 * ((*v + TINY) / I_REF).log10();
    }
}

pub fn third_octave_levels_scalar(sig: &[f64]) -> (Vec<f64>, usize) {
    third_octave_levels_scalar_impl(sig, ParMode::Sequential)
}

fn third_octave_levels_scalar_impl(sig: &[f64], mode: ParMode) -> (Vec<f64>, usize) {
    let n_time = sig.len().div_ceil(DEC_FACTOR);
    let mut out = vec![0.0; N_TOB_BANDS * n_time];
    if n_time == 0 {
        return (out, 0);
    }
    match mode {
        ParMode::Rayon => {
            out.par_chunks_mut(n_time)
                .enumerate()
                .for_each(|(band, out_row)| tol_band_scalar(sig, band, out_row));
        }
        ParMode::Sequential => {
            for (band, out_row) in out.chunks_mut(n_time).enumerate() {
                tol_band_scalar(sig, band, out_row);
            }
        }
    }
    (out, n_time)
}
```

(b) `third_octave_levels_avx2` 加 mode 參數(Task 2 的序列迴圈成為 Sequential 臂):

```rust
#[cfg(target_arch = "x86_64")]
pub unsafe fn third_octave_levels_avx2(sig: &[f64], mode: ParMode) -> (Vec<f64>, usize) {
    let n_time = sig.len().div_ceil(DEC_FACTOR);
    let mut out = vec![0.0; N_TOB_BANDS * n_time];
    if n_time == 0 {
        return (out, 0);
    }
    match mode {
        ParMode::Rayon => {
            out.par_chunks_mut(4 * n_time)
                .enumerate()
                .for_each(|(v, group)| {
                    // SAFETY: dispatch(use_avx2)已驗證 AVX2+FMA 存在。
                    unsafe { tol_group_avx2(sig, v, group, n_time) };
                });
        }
        ParMode::Sequential => {
            for (v, group) in out.chunks_mut(4 * n_time).enumerate() {
                tol_group_avx2(sig, v, group, n_time);
            }
        }
    }
    (out, n_time)
}
```

(c) dispatch(第 148–154 行)改為:

```rust
pub fn third_octave_levels_with_mode(sig: &[f64], mode: ParMode) -> (Vec<f64>, usize) {
    #[cfg(target_arch = "x86_64")]
    if crate::simd::use_avx2() {
        return unsafe { third_octave_levels_avx2(sig, mode) };
    }
    third_octave_levels_scalar_impl(sig, mode)
}

pub fn third_octave_levels(sig: &[f64]) -> (Vec<f64>, usize) {
    third_octave_levels_with_mode(sig, ParMode::Rayon)
}
```

`third_octave_levels(sig)` 簽名不變 → `zwtv/mod.rs:40` 與 `benches/loudness.rs` 兩個呼叫端**零改動**。

- [ ] **Step 3: simd_parity 補 mode 參數**

`tests/simd_parity.rs`:import 補 `use iso532::zwtv::ParMode;`,第 26 行改:

```rust
    let (avx2, avx2_n_time) = unsafe { third_octave_levels_avx2(&sig, ParMode::Sequential) };
```

- [ ] **Step 4: determinism 補 tol 模式等價斷言(R5 前置契約)**

`tests/determinism.rs`:import 區補

```rust
use iso532::zwtv::third_octave_levels::third_octave_levels_with_mode;
use iso532::zwtv::ParMode;
```

`run_hashes` 之前插入:

```rust
fn assert_tol_modes_bitwise_equal(signal: &[f64]) {
    let (r, n_r) = third_octave_levels_with_mode(signal, ParMode::Rayon);
    let (s, n_s) = third_octave_levels_with_mode(signal, ParMode::Sequential);
    assert_eq!(n_r, n_s, "tol n_time");
    assert_eq!(r.len(), s.len(), "tol len");
    for (i, (a, b)) in r.iter().zip(&s).enumerate() {
        assert_eq!(a.to_bits(), b.to_bits(), "tol[{i}]: Rayon={a:e} Sequential={b:e}");
    }
}
```

`#[test]` 內兩處各補一行(auto 段的 `assert_20_runs_identical` 之前、forced scalar 段的 `assert_20_runs_identical` 之前):

```rust
    assert_tol_modes_bitwise_equal(&signal);
```

- [ ] **Step 5: 全量測試 + 雜湊比對**

Run: `cargo test -p iso532`
Expected: 全綠。
Run: `cargo test -p iso532 --test golden_zwtv dump_zwtv_output_hashes -- --ignored --nocapture`
Expected: 12/12 逐字相同。

- [ ] **Step 6: filter_bank 快速 A/B(記錄,不設硬性門檻)**

Run: `cargo bench -p iso532 --bench loudness -- filter_bank_10s`
Expected: avx2 行對 Task 0 基線大幅改善(推估 19.6 → ~4 ms 量級;L3 頻寬競爭可能使收益縮水,記錄實測即可)。

- [ ] **Step 7: Commit**

```bash
git add iso532/src/zwtv/mod.rs iso532/src/zwtv/third_octave_levels.rs iso532/tests/simd_parity.rs iso532/tests/determinism.rs
git commit -m "perf: band-parallel third_octave_levels behind ParMode"
```

---

### Task 4: nl AVX2 kernel 改寫入 per-group slice(序列,單獨 commit)

**Files:**
- Modify: `iso532/src/zwtv/nonlinear_decay.rs`

- [ ] **Step 1: `nl_loudness_process4` 寫入目標改群組切片**

簽名與 store 兩處修改(算術零改動):

```rust
#[cfg(target_arch = "x86_64")]
#[target_feature(enable = "avx2,fma")]
unsafe fn nl_loudness_process4(
    core: &[f64],
    out_group: &mut [f64],
    n_time: usize,
    band: usize,
    b: [f64; 6],
) {
```

函式體開頭(`use std::arch::x86_64::*;` 之後)加:

```rust
    debug_assert_eq!(out_group.len(), 4 * n_time);
```

`k == 0` 的 store 區塊(現行第 228–234 行)改為:

```rust
            if k == 0 {
                let mut lanes = [0.0; 4];
                _mm256_storeu_pd(lanes.as_mut_ptr(), uo);
                for lane in 0..4 {
                    out_group[lane * n_time + t] = lanes[lane];
                }
            }
```

(讀取端 `nl_loudness_load4` 走共享不可變 `&core`,不動。)

- [ ] **Step 2: `nl_loudness_avx2` 改 chunk 分派(序列)**

以群組分派 helper 取代現行 `step_by(4)` 迴圈 + 顯式尾帶(第 122–130 行):

```rust
/// 單一群組分派:滿 4 帶走 process4,尾 chunk(band 20,長度 n_time)走 scalar。
///
/// # Safety
/// Caller must ensure AVX2 and FMA are available before calling.
#[cfg(target_arch = "x86_64")]
unsafe fn nl_group_avx2(core: &[f64], group: &mut [f64], n_time: usize, band: usize, b: [f64; 6]) {
    if group.len() == 4 * n_time {
        nl_loudness_process4(core, group, n_time, band, b);
    } else {
        nl_loudness_band_scalar(&core[band * n_time..(band + 1) * n_time], group, &b);
    }
}
```

`nl_loudness_avx2` 本體(移除其 `#[target_feature]`,理由同 tol——重構後無 intrinsics;保留 `unsafe fn` 與 safety doc):

```rust
#[cfg(target_arch = "x86_64")]
pub unsafe fn nl_loudness_avx2(core: &[f64], n_time: usize) -> Vec<f64> {
    assert_eq!(
        core.len(),
        21 * n_time,
        "nl_loudness expects row-major (21, n_time) core loudness"
    );
    if n_time == 0 {
        return Vec::new();
    }

    let b = nl_coeffs();
    let mut out = vec![0.0; core.len()];

    for (g, group) in out.chunks_mut(4 * n_time).enumerate() {
        nl_group_avx2(core, group, n_time, 4 * g, b);
    }

    out
}
```

(21·n_time 以 4·n_time 切 → 5 個滿群組 + 尾 chunk 恰為 n_time = band 20,與現行顯式尾帶等價。)

- [ ] **Step 3: 全量測試 + 雜湊比對**

Run: `cargo test -p iso532`
Expected: 全綠。
Run: `cargo test -p iso532 --test golden_zwtv dump_zwtv_output_hashes -- --ignored --nocapture`
Expected: 12/12 逐字相同(本 task 算術零改動,僅寫入位址等價改寫)。

- [ ] **Step 4: Commit**

```bash
git add iso532/src/zwtv/nonlinear_decay.rs
git commit -m "refactor: nl avx2 kernel writes into per-group output slice"
```

---

### Task 5: nl 平行化(AVX2 6 工 + scalar 21 工)

**Files:**
- Modify: `iso532/src/zwtv/nonlinear_decay.rs`(平行臂 + 四層入口)
- Modify: `iso532/tests/simd_parity.rs`(`_avx2` 呼叫補 mode)
- Modify: `iso532/tests/determinism.rs`(補 nl 模式等價斷言)

- [ ] **Step 1: nl 四層入口 + 平行臂**

`nonlinear_decay.rs` 檔頭補:

```rust
use super::ParMode;
use rayon::prelude::*;
```

(a) `nl_loudness_avx2` 加 mode 參數:

```rust
#[cfg(target_arch = "x86_64")]
pub unsafe fn nl_loudness_avx2(core: &[f64], n_time: usize, mode: ParMode) -> Vec<f64> {
    assert_eq!(
        core.len(),
        21 * n_time,
        "nl_loudness expects row-major (21, n_time) core loudness"
    );
    if n_time == 0 {
        return Vec::new();
    }

    let b = nl_coeffs();
    let mut out = vec![0.0; core.len()];

    match mode {
        ParMode::Rayon => {
            out.par_chunks_mut(4 * n_time)
                .enumerate()
                .for_each(|(g, group)| {
                    // SAFETY: dispatch(use_avx2)已驗證 AVX2+FMA 存在。
                    unsafe { nl_group_avx2(core, group, n_time, 4 * g, b) };
                });
        }
        ParMode::Sequential => {
            for (g, group) in out.chunks_mut(4 * n_time).enumerate() {
                nl_group_avx2(core, group, n_time, 4 * g, b);
            }
        }
    }

    out
}
```

(b) scalar 拆 `_impl`(公開簽名不變;現行第 27–44 行替換):

```rust
pub fn nl_loudness_scalar(core: &[f64], n_time: usize) -> Vec<f64> {
    nl_loudness_scalar_impl(core, n_time, ParMode::Sequential)
}

fn nl_loudness_scalar_impl(core: &[f64], n_time: usize, mode: ParMode) -> Vec<f64> {
    assert_eq!(
        core.len(),
        21 * n_time,
        "nl_loudness expects row-major (21, n_time) core loudness"
    );

    let b = nl_coeffs();
    let mut out = vec![0.0; core.len()];
    if n_time == 0 {
        return out;
    }

    match mode {
        ParMode::Rayon => {
            out.par_chunks_mut(n_time)
                .enumerate()
                .for_each(|(band, out_row)| {
                    nl_loudness_band_scalar(&core[band * n_time..(band + 1) * n_time], out_row, &b);
                });
        }
        ParMode::Sequential => {
            for (band, out_row) in out.chunks_mut(n_time).enumerate() {
                nl_loudness_band_scalar(&core[band * n_time..(band + 1) * n_time], out_row, &b);
            }
        }
    }

    out
}
```

(c) dispatch(現行第 242–250 行)改為:

```rust
pub fn nl_loudness_with_mode(core: &[f64], n_time: usize, mode: ParMode) -> Vec<f64> {
    #[cfg(target_arch = "x86_64")]
    {
        if crate::simd::use_avx2() {
            return unsafe { nl_loudness_avx2(core, n_time, mode) };
        }
    }
    nl_loudness_scalar_impl(core, n_time, mode)
}

pub fn nl_loudness(core: &[f64], n_time: usize) -> Vec<f64> {
    nl_loudness_with_mode(core, n_time, ParMode::Rayon)
}
```

`nl_loudness(core, n_time)` 簽名不變 → `zwtv/mod.rs:51` 呼叫端零改動。

- [ ] **Step 2: simd_parity 補 mode**

第 49 行改:

```rust
    let avx2 = unsafe { nl_loudness_avx2(&core, n_time, ParMode::Sequential) };
```

(import 已在 Task 3 加過。)

- [ ] **Step 3: determinism 補 nl 模式等價斷言**

import 補 `use iso532::zwtv::nonlinear_decay::nl_loudness_with_mode;`,並插入(合成 core 配方沿用 simd_parity):

```rust
fn synth_core(n_time: usize) -> Vec<f64> {
    let mut core = vec![0.0; 21 * n_time];
    for band in 0..21 {
        for t in 0..n_time {
            let phase = (t as f64 / 40.0 + band as f64).sin();
            core[band * n_time + t] = (phase * 0.6 + 0.5).max(0.0);
        }
    }
    core
}

fn assert_nl_modes_bitwise_equal() {
    let n_time = 500;
    let core = synth_core(n_time);
    let r = nl_loudness_with_mode(&core, n_time, ParMode::Rayon);
    let s = nl_loudness_with_mode(&core, n_time, ParMode::Sequential);
    for (i, (a, b)) in r.iter().zip(&s).enumerate() {
        assert_eq!(a.to_bits(), b.to_bits(), "nl[{i}]: Rayon={a:e} Sequential={b:e}");
    }
}
```

`#[test]` 內兩處 `assert_tol_modes_bitwise_equal(&signal);` 之後各補:

```rust
    assert_nl_modes_bitwise_equal();
```

- [ ] **Step 4: 全量測試 + 雜湊比對**

Run: `cargo test -p iso532`
Expected: 全綠。
Run: `cargo test -p iso532 --test golden_zwtv dump_zwtv_output_hashes -- --ignored --nocapture`
Expected: 12/12 逐字相同。

- [ ] **Step 5: Commit**

```bash
git add iso532/src/zwtv/nonlinear_decay.rs iso532/tests/simd_parity.rs iso532/tests/determinism.rs
git commit -m "perf: band-parallel nl_loudness behind ParMode"
```

---

### Task 6: 效能驗證、lint 收尾、回填

- [ ] **Step 1: bench A/B(準則 3;機器閒置)**

Run(多執行緒): `cargo bench -p iso532 --bench loudness -- zwtv_10s`
Run(單執行緒): `RAYON_NUM_THREADS=1 cargo bench -p iso532 --bench loudness -- zwtv_10s`
Run(filter bank 兩種): `cargo bench -p iso532 --bench loudness -- filter_bank_10s`(+ `RAYON_NUM_THREADS=1` 版)
Expected:
- **MT avx2 zwtv_10s 落在 45–55 ms 區間**(對 Task 0 基線 ~69.3 ms)。若改善不足(如 L3 頻寬競爭,總收益 <2×),記錄實測數字回報並引主計畫風險 #1 的群組配對討論——**回報不重工,不阻擋合入**。
- **ST avx2 zwtv_10s 劣化 ≤2%**(對 ~244.7 ms);ST scalar 對 ~535.5 ms 同準。超標則回查(常見原因:Sequential 臂多了不必要的間接層)。
- MT scalar zwtv_10s 預期明顯改善(對 ~363 ms;無硬性目標,記錄即可)。
- Task 3 後量過 filter_bank 的話,本步 zwtv_10s 的(Task 5 後 − Task 3 後)差值即 nl 的直接歸因。

- [ ] **Step 2: lint 與格式**

Run: `cargo clippy --all-targets -- -D warnings`
Expected: 乾淨。
Run: `cargo fmt --check`
Expected: 乾淨。
(有就地修時單獨 commit:`chore: clippy/fmt cleanup for band-parallel stages`)

- [ ] **Step 3: 回填實測數字到主計畫**

把 Task 0(前)與 Step 1(後)數字回填 `docs/superpowers/plans/2026-07-05-roadmap-master-plan.md` R4 節驗收準則之後:

```markdown
> **實測回填(YYYY-MM-DD,Ryzen 5 3600,機器閒置):** 多執行緒 AVX2 <前> → <後> ms;單執行緒 AVX2 <前> → <後> ms(劣化 <2% 準則:達成/未達成);多執行緒 scalar <前> → <後> ms。filter_bank_10s MT <前> → <後> ms。逐位比對 12/12 相同;determinism 20 次跑逐位相同。
```

```bash
git add docs/superpowers/plans/2026-07-05-roadmap-master-plan.md
git commit -m "docs: record R4 measured perf numbers in master plan"
```

---

## Self-Review 紀錄

- **範圍覆蓋:** 主計畫 R4 三項——`third_octave_levels.rs` 7 工(Task 2+3)、`nonlinear_decay.rs` 6 工(Task 4+5)、ParMode 預留(Task 3 Step 1,R5 契約由 determinism 模式等價斷言看守)。四條驗收分別落在:準則 1 = 每個行為 commit 後的雜湊比對(Task 2/3/4/5)、準則 2 = simd_parity 持續全綠(且改走 Sequential 臂)、準則 3 = Task 6 Step 1、準則 4 = Task 1(先於任何平行化落地)。主計畫 4 項風險 + 探索新增 5 項風險各有緩解落點(見風險表)。
- **兩步式歸因:** 每個檔案「結構重構(序列)→ 翻平行」各自單獨 commit,4 個行為 commit 各有雜湊檢查點,出錯可 bisect 直接歸因。
- **呼叫端盤點:** `third_octave_levels` 僅 `zwtv/mod.rs:40` 與 bench 呼叫、`nl_loudness` 僅 `zwtv/mod.rs:51`、`_scalar`/`_avx2` 變體僅測試呼叫——四層簽名設計下,`src` 呼叫端與 golden 測試**零改動**,僅 simd_parity 兩行補 mode 參數。
- **型別一致:** 所有程式碼區塊對照現行原始碼(2026-07-09 HEAD)的簽名、常數名(`DEC_FACTOR`/`TINY`/`I_REF`/`N_TOB_BANDS`/`TOB_GAIN`/`TOB_DELTA`)、行號撰寫;無佔位符,所有指令附預期輸出。
- **R1 遺留項處置:** #2(nl time-major)評估後排除(與 band-major chunk 分派衝突,見範圍外);#1/#3/#4 明確範圍外。

---

## 審查紀錄(2026-07-10,Claude)

**審查對象:** Codex 依本計畫完成的實作,審查時全部位於未提交工作區(HEAD = 9d8c496,R1)。範圍 8 檔:`third_octave_levels.rs`、`nonlinear_decay.rs`、`zwtv/mod.rs`、`tests/{common/mod,golden_zwtv,simd_parity,determinism}.rs`(docs 與 .gitignore 的工作區改動為 R4 之前既有,非本階段產物)。

**方法:** 8 角度 finder(逐行/移除行為稽核/跨檔追蹤/重用/簡化/效率/altitude/慣例)+ 逐項驗證;全測試套件、雜湊 dump、clippy `-D warnings`、fmt 皆綠;效能以 **git worktree 檢出 R1 commit 做同日同機 A/B**。

### 驗收結果:4/4 通過

| 準則 | 結果 |
|---|---|
| 1. golden 逐位不變 | ✅ `dump_zwtv_output_hashes` 12/12 與 R1 記錄逐字相同 |
| 2. simd_parity 不變 | ✅ 全綠(改走 `ParMode::Sequential` 臂) |
| 3. 效能 | ✅ MT AVX2 **74.2 → 52.2 ms**(−30%,落在 45–55 區間);ST 同日 A/B:AVX2 249.0 → 252.8 ms(**+1.5%**)、scalar 553.9 → 558.0 ms(**+0.7%**),皆 ≤2% |
| 4. 決定性 20 次跑 | ✅ 通過(auto + forced-scalar) |

**量測方法學教訓(補強 R1 教訓):** 直接對 R1 的歷史數字比對得到 ST +3~5% 假警報——連未改動的 scalar ST 路徑都「劣化」4%,證明跨日機器條件不可比。**ST ≤2% 這類緊預算驗收必須同日 A/B(worktree 檢出基準 commit 重量)。** 歸因:`filter_bank_10s` ST AVX2 21.6 → 24.3 ms(+2.7 ms)= tol 迴圈互換(1 趟掃訊號 → 7 趟)的實測成本,攤到管線 +1.1%,在預算內;風險 #1「回報不重工」適用,不啟動群組配對 fallback。

### 風險核對:9 項中 6 項確實避開,3 項部分

| # | 風險 | 狀態 |
|---|---|---|
| 1 | L3 頻寬競爭 | ✅ 已實測(MT −30%;tol 互換 +2.7 ms 被吸收) |
| 2 | false sharing | ✅ `par_chunks_mut` 連續互斥切片 |
| 3 | rayon 巢狀 / R5 須 Sequential | ⚠️ ParMode 型別就位,但註解遺漏計畫指定的 R5 契約文字 |
| 4 | 群組狀態誤共享 | ✅ 狀態全為 kernel 區域變數 |
| 5 | `chunks_mut(0)` panic | ✅ 四路徑守衛齊全 |
| 6 | `#[target_feature]` × closure | ✅ 屬性僅存於含 intrinsics 的 kernel;closure 以 `unsafe`+SAFETY 呼叫 |
| 7 | scalar 平行暫態記憶體 | ⚠️ 行為如計畫接受,但「離線限定」註記未寫入文件 |
| 8 | FORCE_SCALAR race | ✅ determinism.rs 單一 `#[test]` 獨立 binary |
| 9 | Sequential 臂 bit-rot | ⚠️ 等價斷言就位,但被 `use_rayon` 計畫外條件在 1 緒環境架空 |

### 發現(7 項,無正確性缺陷)

1. **[CONFIRMED] Task 6 未執行**:bench 數字未記錄、主計畫 R4 節無回填(審查已代跑補齊,數字見上表)。
2. **[CONFIRMED] commit 結構未執行**:計畫的 5 commit / 4 雜湊檢查點全部未建,bisect 歸因喪失(終態正確性已由審查獨立驗證)。
3. **[CONFIRMED] `use_rayon()` 計畫外條件**(`mod.rs:19`):`current_num_threads() > 1` 使 `ParMode::Rayon` 在 1 緒 pool 靜默走 Sequential 臂 → determinism 雙臂等價斷言在 `RAYON_NUM_THREADS=1` 環境空洞化,平行臂無法強制。
4. **[CONFIRMED] ParMode 註解遺漏 R5 契約文字**與暫態記憶體註記(風險 #3/#7 的指定緩解落點)。
5. **[PLAUSIBLE] `nl_group_avx2` 以切片長度推斷尾帶**,「短 chunk = 恰 1 帶」僅因 21 % 4 == 1 成立,未明示。
6. **[PLAUSIBLE] 排程樣板 4 處重複**(tol/nl × scalar/avx2),可收斂為單一 `chunks_dispatch` helper;附帶 `n_time==0` 守衛 3 種寫法不一。
7. **[PLAUSIBLE] 測試配方重複**:`synth_core` 與 simd_parity、`synth_signal` 與 bench 配方逐字重複,可下沉 `tests/common`。

**跨檔盤點:** 所有呼叫端一致——golden 走 `_scalar`(未變)、simd_parity 補 `Sequential`、determinism 走 `_with_mode`、bench 與 `mod.rs` 走原公開入口;`fnv1a_f64` 全 repo 僅存 common 一份。

**處置(2026-07-10,三議題全採上策):** 議題 1 = `use_rayon` 回歸純 `match mode` 並補 ParMode 的 R5 契約註解(發現 3/4 清零,改後全套驗證重跑);議題 2 = 分 4 commit 進版、逐 commit 驗證;議題 3 = 主計畫 R4 節回填實測數字 + X2 慣例納入「同日 A/B(worktree)」方法學。發現 5–7 為低優先清理,建議 R5 前順手處理。收尾文件:`docs/R4-REVIEW-CLOSEOUT-2026-07-10.md`。
