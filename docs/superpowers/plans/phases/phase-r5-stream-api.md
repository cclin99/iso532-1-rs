# R5 串流 API 重構 + phon 轉換 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把批次 zwtv 管線重構為零配置、無 rayon、可任意 chunk 餵入的 `ZwtvStream`，加上 sone→phon 轉換與 P0 硬化（denormal/NaN/前視/120 dB 語意），最後以 `iso532_stream_*` 擴充 C ABI 並凍結 v1。

**Architecture:** 三個階段 kernel（third_octave_levels / nonlinear_decay / temporal_weighting）先「狀態化」——把濾波器狀態抽成 struct、暴露單幀推進入口，批次路徑改為驅動同一份狀態化 kernel（golden 逐位不變是每一步的硬 gate）。`ZwtvStream` 之後只是這些狀態物件的薄協調器：nl 持有 1 幀 lookahead、tw 拆半發射，總延遲恰 1 內部幀（24 樣本）。等價驗收對 `ZeroState` 參考路徑逐位比對（批次的 nl wraparound 初始化依賴全訊號最後一幀，串流原理上不可重現，見決策 D1）。

**Tech Stack:** Rust 2021、std::arch AVX2/FMA、criterion、cbindgen 0.29.4、pytest（僅 S0）。

**上游計畫:** `docs/superpowers/plans/2026-07-05-roadmap-master-plan.md` §R5（驗收準則逐條複製於本文件 §驗收總表，未改寫——主計畫 X4 慣例）。

---

## 先鎖定決策（主計畫指定「phase 計畫開頭必須定案」的項目）

### D1. 等價基準 = `ZeroState` 參考路徑（為什麼不能直接對 golden 逐位）

`nl_loudness_band_scalar`（`nonlinear_decay.rs:88`）在 col=0 讀 `uo[n_inner-1]`，而 `uo = ui_delta.clone()`——**第 0 幀的輸出依賴整段訊號最後一幀**（AVX2 版在 `nonlinear_decay.rs:210-214` 把同一語意寫成顯式 seed）。串流沒有「最後一幀」，原理上不可重現。因此：

- 等價驗收（E2）對 **ZeroState 參考**逐位：同一套狀態化 kernel、nl 初始 `(prev_uo, prev_u2) = (0, 0)`、以批次陣列形式驅動（`#[doc(hidden)] pub fn zwtv_reference_zerostate`，見 Task S3.1）。
- 對正式 golden 的關係（E3）：暫態以 nl 最慢時間常數 τ_var=75 ms 與 tw slow τ=70 ms 衰減。實作量測證明原 5τ+5τ 推導不足（frame 363 差值仍為 1.7133437069e-7；第一個持續 ≤1e-9 的 frame 為 544），因此 **N_WARMUP_FRAMES = ceil((8×0.075 + 8×0.070)/0.002) = 580**（2 ms 輸出幀），保留 36-frame margin 且不放寬 atol 1e-9。

### D2. FTZ/denormal 決策（主計畫風險 #2「不要寫到一半才發現」）

x86_64 上 **MXCSR 的 FTZ/DAZ 同時作用於 scalar SSE f64 與 AVX2**——Rust 的 scalar f64 運算就是 SSE 指令。因此：

- `ZwtvStream::push`/`flush` 以 RAII `DenormalGuard`（`_mm_getcsr`/`_mm_setcsr`，FTZ bit15 | DAZ bit6 = `0x8040`，`Drop` 還原）包整個函式體。**不做主計畫草案中的 scalar 手動沖洗**——guard 已覆蓋 scalar 路徑，手動沖洗反而破壞與參考路徑的逐位一致。
- 等價測試（E2/E3）把參考路徑的生成**也包在同一個 guard 作用域內**，兩側數值環境相同 → 逐位比較成立。
- 公開批次 API 的數值行為完全不動（guard 只在 stream 入口）。
- aarch64（R7）：FPCR FZ bit 的對應 guard 留 `#[cfg]` TODO 註解，不在本階段實作。

### D3. flush 語意 = 批次尾端語意（next = 0.0），偏離主計畫風險 #7 的「重複末幀」建議

批次對最後一幀的內插一律用 `next = 0.0`（nl `nonlinear_decay.rs:72`、tw `temporal_weighting.rs:11-15`）。flush 採同一語意 → **批次等價含最末幀、無需排除**，嚴格優於「重複末幀」方案（該方案要在等價測試排除末幀）。風險 #7 擔心的假性下沉本來就是批次的既有尾端行為，文件化即可。

### D4. 延遲 = 恰 1 內部幀（24 樣本），由「nl 持有 1 幀 + tw 拆半發射」達成

- nl 幀 t 的完整處理需要 core[t+1]（子步 k≥1 的內插）→ nl 持有 1 幀，收到 core[t] 時處理幀 t−1。
- tw 幀 t 的發射值只需 loudness[t]（子步 k=0），k=1..23 需要 loudness[t+1] → 收到 loudness[t] 時**先補完幀 t−1 的 k=1..23，再算幀 t 的 k=0 並發射**。零額外延遲。
- 兩者相加 = 1 幀，`latency_samples() = 24` 與主計畫鎖定值吻合。若兩級都用「持有 1 幀」會變 2 幀——**不要那樣做**。

### D5. kernel 路徑釘選與捨入差異

- scalar nl 用 `(next - row) / 24.0`（除法），AVX2 用 `× (1/24)`（倒數乘法）——**捨入不同，不是等價寫法**。狀態化時各自逐字保留原運算式。
- 串流以 `crate::simd::use_avx2()` 自動選 kernel，與批次一致；等價測試兩路徑都跑（scalar 路徑沿用既有 FORCE_SCALAR 單測試 binary 慣例，見 `iso532/tests/simd_dispatch.rs` 的做法）。

### D6. v1 串流不輸出 specific loudness；N 全走 `calc_slopes_n_only`

R1 已建立並以測試釘死 `calc_slopes_into` 與 `calc_slopes_n_only` 對同一幀的 N 逐位相等，串流每幀都走 `n_only`（240 點 spec 是批次在 t%4==0 幀才算的輸出，v1 串流不提供，留第二 out 參數擴充）。

### D7. 串流的輸入契約與批次的差異（文件化，不是 bug）

- 串流不驗 `SignalTooShort`（即時輸入沒有「總長」概念）；不收 `fs` 參數（48 kHz 烘焙，rustdoc 明載）。
- \>120 dB 幀：夾限 + `CLAMPED_120DB` flag，不回 Err（批次語意不動）。
- 非有限樣本：置 0 + `NONFINITE_INPUT` flag。
- flags 自上次發射後累積（OR），附在下一個發射的 StreamFrame 上。

---

## File Structure

| 檔案 | 動作 | 職責 |
|---|---|---|
| `iso532/src/sone2phon.rs` | Create | sone→phon 轉換（純函式） |
| `iso532/src/zwtv/stream.rs` | Create | `ZwtvStream`/`StreamFrame`/`FrameFlags`/`DenormalGuard`/ZeroState 參考 |
| `iso532/src/zwtv/third_octave_levels.rs` | Modify | `TolBandState`（scalar）/`TolGroupState`（AVX2）狀態化；批次改driver |
| `iso532/src/zwtv/nonlinear_decay.rs` | Modify | `NlBandState`/`NlGroupState` 狀態化；批次改 driver；S0 尾帶明示參數 |
| `iso532/src/zwtv/temporal_weighting.rs` | Modify | `TwState` 狀態化；批次改 driver |
| `iso532/src/core/main_loudness.rs` | Modify | 抽 `main_loudness_unchecked` + 新增 `main_loudness_clamped` |
| `iso532/src/zwtv/mod.rs` | Modify | S0 `chunks_dispatch` helper；`pub mod stream` |
| `iso532/src/lib.rs` | Modify | 匯出 stream 型別與 sone2phon |
| `iso532/tests/stream.rs` | Create | chunk 不變性、ZeroState 等價、warmup 收斂、P0 看守 |
| `iso532/tests/stream_alloc.rs` | Create | counting allocator 零配置證明（獨立 binary） |
| `iso532/tests/stream_no_rayon.rs` | Create | push 不建 thread pool 證明（獨立 binary） |
| `iso532/tests/common/mod.rs` | Modify | S0 `synth_signal`/`synth_core` 下沉 |
| `iso532/benches/`（既有 bench 檔） | Modify | `stream_push` criterion 基準 |
| `iso532-ffi/src/lib.rs` | Modify | `iso532_stream_*` 5 函式 + `Iso532StreamFrame` |
| `iso532-ffi/tests/ffi.rs` | Modify | 串流 ABI 測試 |
| `iso532-ffi/include/iso532.h` | Regen | cbindgen 0.29.4 重生 + v1 凍結標註 |
| `iso532-py/tests/conftest.py` | Create | S0：sys.path bootstrap 集中 + REQUIRE_PARITY 實作 |

**時程推估:** S0 0.5 天、S1 0.5 天、S2 3–4 天、S3 1 天、S4 2–3 天、S5 1–2 天、S6 1 天、S7 1–2 天 ≈ 10–14 天（主計畫 8–12 天的上緣，含 S0 清理）。

## 驗收總表（主計畫 §R5 原文逐條，缺一不收）

1. **chunk 尺寸不變性:** 同一訊號以 chunk 尺寸 {1, 7, 24, 64, 480, 4096, 隨機序列} 餵入，輸出逐位相同。
2. **批次等價:** 對 9 組 golden 訊號，串流輸出與 `InitMode::ZeroState` 批次參考逐位一致；與現行批次 golden 的差異僅限前 N_warmup 幀（N_warmup 由 nl/tw 時間常數推導，寫入文件）。→ 本計畫具體化為 E2（逐位）+ E3（t≥580 幀 atol 1e-9），見 D1。
3. **零配置:** push 路徑以配置計數 hook 證明 0 allocation。
4. **無 rayon:** push 路徑不觸發 thread pool 建立。
5. 單幀成本 ≤ 60 µs（單執行緒 AVX2；scalar 路徑 ≤ 200 µs 預算內並記錄實測）。
6. sone2phon 對鎖定公式 atol 1e-12（公式即契約，源自主計畫 §R5；mosqito 1.2.1 無獨立公開函式可直接 import，故 py 側以公式重述互驗）。

**全程鐵律:** 每個 commit 後 `cargo test` 全綠 + `hash_gate` 通過；S2 每步另跑 `--test golden_zwtv dump_zwtv_output_hashes -- --ignored --nocapture` 核對 12/12 雜湊與 R1 記錄逐字相同。fmt/clippy 乾淨才 commit。

---

# Phase S0：前置清理（R4 收尾 §3 遺留 + R3 複審殘渣——先前聲稱已修但 repo 未落地的七項）

### Task S0.1: nl AVX2 尾帶改明示帶數參數

**Files:**
- Modify: `iso532/src/zwtv/nonlinear_decay.rs:137-167`

- [ ] **Step 1: 改 `nl_group_avx2` 簽名與兩個呼叫端**

```rust
/// Dispatch one output group: full 4-band groups use AVX2, the final
/// single-band tail uses scalar processing. `n_bands` 由呼叫端明示
/// (4 或 1),不再從切片長度推斷(21 % 4 == 1 的巧合不可依賴)。
///
/// # Safety
/// Caller must ensure AVX2 and FMA are available before calling.
#[cfg(target_arch = "x86_64")]
unsafe fn nl_group_avx2(
    core: &[f64],
    group: &mut [f64],
    n_time: usize,
    band: usize,
    n_bands: usize,
    b: [f64; 6],
) {
    debug_assert_eq!(group.len(), n_bands * n_time);
    if n_bands == 4 {
        // SAFETY: caller has verified AVX2+FMA availability.
        unsafe { nl_loudness_process4(core, group, n_time, band, b) };
    } else {
        debug_assert_eq!(n_bands, 1);
        nl_loudness_band_scalar(&core[band * n_time..(band + 1) * n_time], group, &b);
    }
}
```

兩個呼叫端（rayon 臂與 sequential 臂）改為：

```rust
        out.par_chunks_mut(4 * n_time)
            .enumerate()
            .for_each(|(g, group)| {
                let n_bands = if 4 * g + 4 <= 21 { 4 } else { 21 - 4 * g };
                // SAFETY: dispatch has already verified AVX2+FMA availability.
                unsafe { nl_group_avx2(core, group, n_time, 4 * g, n_bands, b) };
            });
```

（sequential 臂同形，`for (g, group) in out.chunks_mut(4 * n_time).enumerate()`。）

- [ ] **Step 2: 驗證**

Run: `cd iso532 && cargo test && cargo test --test golden_zwtv dump_zwtv_output_hashes -- --ignored --nocapture`
Expected: 全綠；12/12 雜湊與 R1 記錄逐字相同。

- [ ] **Step 3: Commit**

```bash
git add iso532/src/zwtv/nonlinear_decay.rs
git commit -m "refactor: pass explicit band count to nl_group_avx2 (R4 closeout item 1)"
```

### Task S0.2: 排程樣板收斂為 `chunks_dispatch`

**Files:**
- Modify: `iso532/src/zwtv/mod.rs`（`use_rayon` 附近）
- Modify: `iso532/src/zwtv/third_octave_levels.rs:64-72,163-175`
- Modify: `iso532/src/zwtv/nonlinear_decay.rs:47-57,137-149`

- [ ] **Step 1: 在 `zwtv/mod.rs` 新增 helper（取代 `use_rayon`）**

```rust
/// 四個頻帶平行點(tol/nl × scalar/avx2)共用的排程樣板:
/// `out` 按 `chunk` 切互斥片段,Rayon 模式平行、Sequential 依序。
/// 空輸出直接返回(統一 n_time==0 守衛)。
pub(crate) fn chunks_dispatch<F>(out: &mut [f64], chunk: usize, mode: ParMode, f: F)
where
    F: Fn(usize, &mut [f64]) + Sync,
{
    if out.is_empty() {
        return;
    }
    match mode {
        ParMode::Rayon => out
            .par_chunks_mut(chunk)
            .enumerate()
            .for_each(|(g, piece)| f(g, piece)),
        ParMode::Sequential => {
            for (g, piece) in out.chunks_mut(chunk).enumerate() {
                f(g, piece)
            }
        }
    }
}
```

- [ ] **Step 2: 四個呼叫點改用 helper**（以 tol AVX2 為例，其餘三處同形）

```rust
    super::chunks_dispatch(&mut out, 4 * n_time, mode, |v, group| {
        // SAFETY: dispatch has already verified AVX2+FMA availability.
        unsafe { tol_group_avx2(sig, v, group, n_time) };
    });
```

nl AVX2 閉包內含 S0.1 的 `n_bands` 計算。改完後刪除 `use_rayon`（無呼叫者即刪；若 determinism 測試引用，改斷言 `chunks_dispatch` 兩臂等價——現行 determinism 測試是黑箱跑 20 次，不受影響）。

- [ ] **Step 3: 驗證 + Commit**

Run: `cd iso532 && cargo test && cargo clippy --all-targets -- -D warnings`（雜湊 gate 同 S0.1）
Expected: 全綠、12/12 相同。

```bash
git add iso532/src/zwtv/
git commit -m "refactor: unify band-parallel scheduling into chunks_dispatch (R4 closeout item 2)"
```

### Task S0.3: 測試配方下沉 `tests/common`

**Files:**
- Modify: `iso532/tests/common/mod.rs`（新增 `synth_signal`/`synth_core`）
- Modify: `iso532/tests/determinism.rs:11,22`、`iso532/tests/hash_gate.rs:41`（改 use common）

- [ ] **Step 1: 把 `determinism.rs` 的 `synth_signal`/`synth_core` 函式體原封搬入 `tests/common/mod.rs`（`pub fn`），三個測試檔刪本地副本改 `common::synth_signal()`**。**逐字搬移，一個字元都不能改**——`hash_gate` 的凍結雜湊直接依賴 `synth_signal` 的輸出位元。先 diff 確認 `hash_gate.rs:41` 與 `determinism.rs:11` 的函式體完全相同再合併；若不同，保留各自版本並在本 task 記錄放棄理由（不能為了 DRY 動凍結輸入）。

- [ ] **Step 2: 驗證 + Commit**

Run: `cd iso532 && cargo test --test determinism --test hash_gate --test simd_parity`
Expected: 全綠（hash_gate 凍結值不變）。

```bash
git add iso532/tests/
git commit -m "test: dedupe synth fixtures into tests/common (R4 closeout item 3)"
```

### Task S0.4: conftest 集中 bootstrap + 真正實作 `ISO532_REQUIRE_PARITY`

**Files:**
- Create: `iso532-py/tests/conftest.py`
- Modify: `iso532-py/tests/test_smoke.py:2-9`、`iso532-py/tests/test_parity_mosqito.py:9-25`
- Modify: `docs/R3-REVIEW-FIXES-IMPLEMENTATION-2026-07-11.md:38`（訂正與現實不符的敘述）

- [ ] **Step 1: 寫 conftest.py**

```python
"""Shared test bootstrap: tools/ on sys.path + parity enforcement switch."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

REQUIRE_PARITY = os.environ.get("ISO532_REQUIRE_PARITY") == "1"
```

- [ ] **Step 2: test_smoke.py 刪 `sys`/`Path` import 與 `sys.path.insert` 行（conftest 先載入）；test_parity_mosqito.py 開頭改為**

```python
import numpy as np
import pytest

from conftest import REQUIRE_PARITY

if REQUIRE_PARITY:
    import mosqito  # noqa: F401  強制模式:缺依賴 = 紅,不是 skip
    import iso532
else:
    pytest.importorskip("mosqito")
    iso532 = pytest.importorskip("iso532")
from mosqito.sq_metrics import loudness_zwst, loudness_zwtv  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
if not (ROOT / "data" / "annexb").is_dir():
    if REQUIRE_PARITY:
        raise RuntimeError("ISO532_REQUIRE_PARITY=1 but data/annexb missing")
    pytest.skip("data/annexb missing — run tools/setup_env.sh", allow_module_level=True)
from gen_golden import FS, make_signals  # noqa: E402
```

（保留原有 `import sys`/`Path` 供 ROOT 用；刪掉 `sys.path.insert(0, str(ROOT / "tools"))` 行——conftest 已插。）

- [ ] **Step 3: 訂正實作紀錄**——`docs/R3-REVIEW-FIXES-IMPLEMENTATION-2026-07-11.md:38` 該行句尾加註：「（2026-07-11 追記:conftest 於 R5 S0.4 才真正落地;`ISO532_REQUIRE_PARITY` 同步由文件慣例改為程式實作。）」

- [ ] **Step 4: 驗證 + Commit**

Run: `cd iso532-py && ../.venv/Scripts/python.exe -m pytest tests/test_smoke.py -v && ISO532_REQUIRE_PARITY=1 ../.venv/Scripts/python.exe -m pytest tests/test_parity_mosqito.py -v`
Expected: smoke 6/6；parity 18 passed / 0 skipped。再驗負向：`ISO532_REQUIRE_PARITY=1` 且暫時改名 `data/annexb` 時 collection 直接 error（改回）。

```bash
git add iso532-py/tests/ docs/R3-REVIEW-FIXES-IMPLEMENTATION-2026-07-11.md
git commit -m "test: centralize py bootstrap in conftest, implement ISO532_REQUIRE_PARITY (R3 residues)"
```

---

# Phase S1：sone2phon + StreamFrame/FrameFlags（無依賴，先回血）

### Task S1.1: sone2phon

**Files:**
- Create: `iso532/src/sone2phon.rs`
- Modify: `iso532/src/lib.rs`（`mod sone2phon; pub use sone2phon::sone2phon;`）

- [ ] **Step 1: 寫失敗測試**（放在 `sone2phon.rs` 的 `#[cfg(test)] mod tests`）

```rust
#[test]
fn anchors_and_monotonicity() {
    assert_eq!(sone2phon(1.0), 40.0);
    assert_eq!(sone2phon(2.0), 50.0);
    assert_eq!(sone2phon(4.0), 60.0);
    assert!((sone2phon(0.5) - 40.0 * 0.5005_f64.powf(0.35)).abs() < 1e-12);
    assert!((sone2phon(0.0) - 40.0 * 0.0005_f64.powf(0.35)).abs() < 1e-12);
    let mut prev = f64::NEG_INFINITY;
    for i in 0..=1000 {
        let p = sone2phon(i as f64 * 0.02);
        assert!(p >= prev, "non-monotonic at {i}");
        prev = p;
    }
}
```

- [ ] **Step 2: `cargo test sone2phon` → FAIL（函式不存在）**

- [ ] **Step 3: 實作**

```rust
//! sone → phon 轉換(ISO 532-1 附錄;mosqito utils 同語意,公式為凍結契約)。

/// `n ≥ 1 → 40 + 10·log2(n)`;`n < 1 → 40·(n + 0.0005)^0.35`。
/// 輸入為非負 sone;負值行為未定義(串流路徑保證 n ≥ 0)。
pub fn sone2phon(n: f64) -> f64 {
    if n >= 1.0 {
        40.0 + 10.0 * n.log2()
    } else {
        40.0 * (n + 0.0005).powf(0.35)
    }
}
```

- [ ] **Step 4: `cargo test sone2phon` → PASS；Commit**

```bash
git add iso532/src/sone2phon.rs iso532/src/lib.rs
git commit -m "feat: sone2phon conversion (R5 master plan formula, frozen contract)"
```

### Task S1.2: FrameFlags + StreamFrame + 凍結測試

**Files:**
- Create: `iso532/src/zwtv/stream.rs`（本 task 只放型別）
- Modify: `iso532/src/zwtv/mod.rs`（`pub mod stream;`）、`iso532/src/lib.rs`（`pub use zwtv::stream::{FrameFlags, StreamFrame, ZwtvStream};` 的前兩項，ZwtvStream 到 S4 再加）

- [ ] **Step 1: 失敗測試（bit 值一經發布不得重排——與錯誤碼同級的凍結契約）**

```rust
#[test]
fn flag_bits_are_frozen() {
    assert_eq!(FrameFlags::CLAMPED_120DB.bits(), 1);
    assert_eq!(FrameFlags::NONFINITE_INPUT.bits(), 2);
    assert_eq!(FrameFlags::WARMUP.bits(), 4);
    assert_eq!(std::mem::size_of::<StreamFrame>(), 32);
}
```

- [ ] **Step 2: 實作（不引入 bitflags 依賴，手刻 8 行）**

```rust
/// StreamFrame 旗標(u32 bit set;bit 值凍結,C ABI 直通)。
#[repr(transparent)]
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct FrameFlags(u32);

impl FrameFlags {
    pub const CLAMPED_120DB: FrameFlags = FrameFlags(1);
    pub const NONFINITE_INPUT: FrameFlags = FrameFlags(1 << 1);
    pub const WARMUP: FrameFlags = FrameFlags(1 << 2);
    pub const fn bits(self) -> u32 {
        self.0
    }
    pub const fn contains(self, other: FrameFlags) -> bool {
        self.0 & other.0 == other.0
    }
    pub fn insert(&mut self, other: FrameFlags) {
        self.0 |= other.0;
    }
    pub fn take(&mut self) -> FrameFlags {
        std::mem::replace(self, FrameFlags(0))
    }
}

/// 一個 2 ms 輸出幀。`repr(C)`:R5 收尾直通 C ABI(`Iso532StreamFrame`)。
#[repr(C)]
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct StreamFrame {
    /// 自串流起點的 2 ms 幀序號(整數推導,無浮點累積)。
    pub t_frame_index: u64,
    /// sone。
    pub n: f64,
    /// phon(= sone2phon(n))。
    pub n_phon: f64,
    pub flags: FrameFlags,
    pub _reserved: u32,
}
```

- [ ] **Step 3: PASS 後 Commit**

```bash
git add iso532/src/zwtv/stream.rs iso532/src/zwtv/mod.rs iso532/src/lib.rs
git commit -m "feat: StreamFrame + FrameFlags with frozen bit layout"
```

---

# Phase S2：kernel 狀態化（每 task 的 gate = golden 逐位不變；這是本階段的 TDD——RED 是「雜湊變了」）

**主計畫風險 #6 的兩步法在此落實:每個 task 只搬狀態、不動語意,commit 粒度 = 一個 kernel。**

### Task S2.1: `TolBandState`（scalar tol 狀態化）

**Files:**
- Modify: `iso532/src/zwtv/third_octave_levels.rs`

- [ ] **Step 1: 新增狀態 struct 與單樣本推進（運算式逐字沿用 `sos.rs` 與 `tol_band_scalar` 的原式）**

```rust
/// 單頻帶 scalar 濾波狀態:3 段 DF2T biquad + 3 級 onepole 平滑。
/// `advance` 每樣本推進,回傳平滑後強度(呼叫端負責 24:1 抽取與 dB 轉換)。
/// 運算式與批次路徑逐字相同——位元等價是契約,不是巧合。
pub(crate) struct TolBandState {
    sos: [Sos; 3],
    z: [[f64; 2]; 3],
    gain: f64,
    sb0: f64,
    sa1: f64,
    sm: [f64; 3],
}

impl TolBandState {
    pub(crate) fn new(band: usize) -> Self {
        let (sb0, sa1) = smoothing_coeff(band);
        Self {
            sos: band_sos(band),
            z: [[0.0; 2]; 3],
            gain: TOB_GAIN[band],
            sb0,
            sa1,
            sm: [0.0; 3],
        }
    }

    #[inline]
    pub(crate) fn advance(&mut self, sample: f64) -> f64 {
        let mut v = sample * self.gain;
        for (s, z) in self.sos.iter().zip(self.z.iter_mut()) {
            let xin = v;
            let y = s.b[0] * xin + z[0];
            z[0] = s.b[1] * xin - s.a[0] * y + z[1];
            z[1] = s.b[2] * xin - s.a[1] * y;
            v = y;
        }
        v = v * v;
        for stage in self.sm.iter_mut() {
            *stage = self.sb0 * v + self.sa1 * *stage;
            v = *stage;
        }
        v
    }
}

/// 平滑強度 → dB(批次與串流共用的唯一出口)。
#[inline]
pub(crate) fn intensity_to_db(v: f64) -> f64 {
    10.0 * ((v + TINY) / I_REF).log10()
}
```

- [ ] **Step 2: `tol_band_scalar` 改為驅動狀態（整函式取代）**

```rust
fn tol_band_scalar(sig: &[f64], band: usize, out_row: &mut [f64]) {
    let mut state = TolBandState::new(band);
    let mut frame = 0usize;
    for (i, &sample) in sig.iter().enumerate() {
        let v = state.advance(sample);
        if i % DEC_FACTOR == 0 {
            out_row[frame] = intensity_to_db(v);
            frame += 1;
        }
    }
}
```

**位元等價論證（寫進 commit message）:** 原路徑是逐級全訊號掃（gain map → sosfilt 段外迴圈 → 平方 → onepole×3 趟）；新路徑逐樣本交錯。每個輸出值的浮點運算圖（運算子、順序、運算元）逐值相同——級間只透過遞迴狀態耦合，無跨樣本混合。golden gate 是實證。

- [ ] **Step 3: gate**

Run: `cd iso532 && cargo test && cargo test --test golden_zwtv dump_zwtv_output_hashes -- --ignored --nocapture`
Expected: 全綠；12/12 雜湊逐字相同。**任何一個雜湊變了就是 Step 1/2 有語意改動——回去逐運算式比對，不許調容差。**

- [ ] **Step 4: Commit**

```bash
git add iso532/src/zwtv/third_octave_levels.rs
git commit -m "refactor: extract TolBandState, batch scalar tol drives it (bitwise-identical)"
```

### Task S2.2: `TolGroupState`（AVX2 tol 狀態化）

**Files:**
- Modify: `iso532/src/zwtv/third_octave_levels.rs:83-149`

- [ ] **Step 1: 把 `tol_group_avx2` 的暫存器狀態抽成 struct（係數設定段 88-118 進 `new`，樣本迴圈體 122-138 進 `advance`，逐字搬移）**

```rust
/// 4 頻帶 AVX2 濾波狀態(f64x4 群組)。指令序列與原 tol_group_avx2 逐字
/// 相同;跨 push 呼叫的暫存器溢出/重載不改變 FP 結果。
#[cfg(target_arch = "x86_64")]
pub(crate) struct TolGroupState {
    gain: std::arch::x86_64::__m256d,
    sb0: std::arch::x86_64::__m256d,
    sa1: std::arch::x86_64::__m256d,
    a1: [std::arch::x86_64::__m256d; 3],
    a2: [std::arch::x86_64::__m256d; 3],
    z0: [std::arch::x86_64::__m256d; 3],
    z1: [std::arch::x86_64::__m256d; 3],
    sm: [std::arch::x86_64::__m256d; 3],
}

#[cfg(target_arch = "x86_64")]
impl TolGroupState {
    /// # Safety: 呼叫端保證 AVX2+FMA 可用。
    #[target_feature(enable = "avx2,fma")]
    pub(crate) unsafe fn new(v: usize) -> Self { /* 原 88-118 行設定段,
        z0/z1/sm 以 _mm256_setzero_pd() 初始化 */ }

    /// # Safety: 同上。回傳平滑後強度向量(lane = 群組內頻帶)。
    #[inline]
    #[target_feature(enable = "avx2,fma")]
    pub(crate) unsafe fn advance(&mut self, sample: f64) -> std::arch::x86_64::__m256d {
        use std::arch::x86_64::*;
        let xs = _mm256_set1_pd(sample);
        let mut y = _mm256_mul_pd(xs, self.gain);
        let b1s = [2.0, 0.0, -2.0];
        let b2s = [1.0, -1.0, 1.0];
        for section in 0..3 {
            let xin = y;
            y = _mm256_add_pd(xin, self.z0[section]);
            let b1v = _mm256_set1_pd(b1s[section]);
            let t = _mm256_fmadd_pd(b1v, xin, self.z1[section]);
            self.z0[section] = _mm256_fnmadd_pd(self.a1[section], y, t);
            let b2v = _mm256_set1_pd(b2s[section]);
            self.z1[section] = _mm256_fnmadd_pd(self.a2[section], y, _mm256_mul_pd(b2v, xin));
        }
        y = _mm256_mul_pd(y, y);
        for stage_state in &mut self.sm {
            *stage_state = _mm256_fmadd_pd(self.sb0, y, _mm256_mul_pd(self.sa1, *stage_state));
            y = *stage_state;
        }
        y
    }
}
```

（`new` 的函式體 = 原 88-118 行逐字，只把區域變數改存欄位。此處不再重印，Codex 從現行檔案搬移——**搬移不重寫**。）

- [ ] **Step 2: `tol_group_avx2` 改 driver**

```rust
#[cfg(target_arch = "x86_64")]
#[target_feature(enable = "avx2,fma")]
unsafe fn tol_group_avx2(sig: &[f64], v: usize, out_group: &mut [f64], n_time: usize) {
    use std::arch::x86_64::*;
    debug_assert_eq!(out_group.len(), 4 * n_time);
    // SAFETY: 本函式已在 avx2+fma target_feature 內。
    let mut state = unsafe { TolGroupState::new(v) };
    let mut frame = 0usize;
    for (i, &sample) in sig.iter().enumerate() {
        let y = unsafe { state.advance(sample) };
        if i % DEC_FACTOR == 0 {
            let mut lanes = [0.0; 4];
            _mm256_storeu_pd(lanes.as_mut_ptr(), y);
            for lane in 0..4 {
                out_group[lane * n_time + frame] = intensity_to_db(lanes[lane]);
            }
            frame += 1;
        }
    }
}
```

- [ ] **Step 3: gate（同 S2.1 Step 3）+ Commit**

```bash
git add iso532/src/zwtv/third_octave_levels.rs
git commit -m "refactor: extract TolGroupState, batch AVX2 tol drives it (bitwise-identical)"
```

### Task S2.3: `NlBandState`（scalar nl 狀態化 + 顯式 seed）

**Files:**
- Modify: `iso532/src/zwtv/nonlinear_decay.rs:62-117`

- [ ] **Step 1: 新增狀態 struct（運算式逐字對應原 87-111 行迴圈體；除法保留除法——見 D5）**

```rust
/// 單頻帶 nl 狀態:上一子步的 (uo, u2)。`advance_frame` 處理一個 2 kHz
/// 幀的 24 個子步,回傳子步 0 的 uo(= 批次 out[t])。
/// 批次以 wraparound seed 建構(mosqito 語意);串流/ZeroState 以 default (0,0)。
#[derive(Clone, Copy, Debug, Default)]
pub(crate) struct NlBandState {
    prev_uo: f64,
    prev_u2: f64,
}

impl NlBandState {
    /// mosqito 的 col=0 wraparound 初始化:prev_uo = 全訊號最後一幀的
    /// 最末虛擬子步(= row_last + (0-row_last)/24 * 23),prev_u2 = 0。
    pub(crate) fn mosqito_seed(row_last: f64) -> Self {
        let delta = (0.0 - row_last) / NL_ITER as f64;
        Self {
            prev_uo: row_last + delta * (NL_ITER - 1) as f64,
            prev_u2: 0.0,
        }
    }

    #[inline]
    pub(crate) fn advance_frame(&mut self, row_t: f64, next: f64, b: &[f64; 6]) -> f64 {
        let delta = (next - row_t) / NL_ITER as f64;
        let mut out0 = 0.0;
        for k in 0..NL_ITER {
            let ui = row_t + delta * k as f64;

            let mut uo = ui;
            let uo2 = self.prev_uo * b[2] - self.prev_u2 * b[3];
            if self.prev_uo > self.prev_u2 && uo2 >= ui {
                uo = uo2;
            }
            let uo2 = self.prev_uo * b[4];
            if self.prev_uo <= self.prev_u2 && uo2 >= ui {
                uo = uo2;
            }

            let mut u2 = uo;
            let u22 = self.prev_uo * b[0] - self.prev_u2 * b[1];
            if ui < self.prev_uo && self.prev_uo > self.prev_u2 && u22 <= uo {
                u2 = u22;
            }
            let u2_2 = (self.prev_u2 - ui) * b[5] + ui;
            if ui >= self.prev_uo && !((ui - self.prev_uo).abs() < 1e-5 && uo <= self.prev_u2) {
                u2 = u2_2;
            }

            if k == 0 {
                out0 = uo;
            }
            self.prev_uo = uo;
            self.prev_u2 = u2;
        }
        out0
    }
}
```

**語意核對清單（實作前先逐條對照原碼確認,不是選配）:**
- 原 `uo = ui_delta.clone()` ⇒ 每子步 uo 預設 = ui ✓（`let mut uo = ui`）。
- 原 `u2[col] = uo[col]` 在兩個 uo 條件之後、兩個 u2 條件之前 ✓。
- `u22 <= uo[col]` 讀的是**本子步已定案的 uo** ✓；`uo[col] <= u2[prev]` 讀**上一子步的 u2** ✓。
- 原碼 62-85 行的 `u2[0] = row[0]*(1.0-b[5])` 預寫入是死碼（col=0 迴圈體無條件先寫 `u2[col]`，且 col=0 的條件讀的是 `u2[prev]=u2[n_inner-1]=0`）——AVX2 kernel 沒有對應物且通過 simd_parity，即為實證。**不搬**，在 commit message 記錄。

- [ ] **Step 2: `nl_loudness_band_scalar` 改 driver**

```rust
fn nl_loudness_band_scalar(row: &[f64], out: &mut [f64], b: &[f64; 6]) {
    let n_time = row.len();
    assert_eq!(out.len(), n_time);
    if n_time == 0 {
        return;
    }
    let mut state = NlBandState::mosqito_seed(row[n_time - 1]);
    for t in 0..n_time {
        let next = if t + 1 < n_time { row[t + 1] } else { 0.0 };
        out[t] = state.advance_frame(row[t], next, b);
    }
}
```

- [ ] **Step 3: gate（同 S2.1 Step 3；simd_parity 也必須綠）+ Commit**

```bash
git add iso532/src/zwtv/nonlinear_decay.rs
git commit -m "refactor: extract NlBandState with explicit seed, batch scalar nl drives it (bitwise-identical; dead u2[0] pre-init dropped, AVX2 parity is the evidence)"
```

### Task S2.4: `NlGroupState`（AVX2 nl 狀態化）

**Files:**
- Modify: `iso532/src/zwtv/nonlinear_decay.rs:188-276`

- [ ] **Step 1: 同 S2.2 手法**——`nl_loudness_process4` 的 `prev_uo`/`prev_u2` 進 struct，常數（`b0..b5`/`inv_iter`/`eps`）打包成 `NlConsts`（`new` 一次建好），子步迴圈體 225-274 行逐字進 `advance_frame(row: __m256d, next: __m256d) -> __m256d`（回傳 k=0 的 uo 向量）。wraparound seed（210-214 行）成為 `NlGroupState::mosqito_seed(last_row: __m256d, consts: &NlConsts)`。`nl_loudness_process4` 改 driver：seed → 迴圈 load row/next → `advance_frame` → 存 k=0 lanes。**倒數乘法 `inv_iter` 保留倒數乘法（D5）。**

- [ ] **Step 2: gate（含 simd_parity）+ Commit**

```bash
git add iso532/src/zwtv/nonlinear_decay.rs
git commit -m "refactor: extract NlGroupState/NlConsts, batch AVX2 nl drives it (bitwise-identical)"
```

### Task S2.5: `TwState`（temporal weighting 狀態化 + 拆半發射）

**Files:**
- Modify: `iso532/src/zwtv/temporal_weighting.rs`（整檔重構）

- [ ] **Step 1: 實作**

```rust
const LP_ITER: usize = 24;
const SAMPLE_RATE: f64 = 2000.0;

fn lp_coeff(tau: f64) -> (f64, f64) {
    let a1 = (-1.0 / (SAMPLE_RATE * LP_ITER as f64 * tau)).exp();
    (1.0 - a1, a1)
}

/// fast(3.5 ms)+slow(70 ms) 雙 lowpass 狀態,拆半發射:
/// 收到 loudness[t] 時先補完幀 t-1 的子步 k=1..23(其內插需要
/// loudness[t]),再算幀 t 的子步 k=0 並回傳輸出——發射零額外延遲。
/// 批次幀 t 的子步順序 = k=0 先記錄輸出、k=1..23 推進;本結構把同一
/// 條運算鏈按資料到達順序重新歸組,逐值位元相同。
pub(crate) struct TwState {
    y_fast: f64,
    y_slow: f64,
    bf: (f64, f64),
    bs: (f64, f64),
    prev: f64,
    has_prev: bool,
}

impl TwState {
    pub(crate) fn new() -> Self {
        Self {
            y_fast: 0.0,
            y_slow: 0.0,
            bf: lp_coeff(3.5e-3),
            bs: lp_coeff(70e-3),
            prev: 0.0,
            has_prev: false,
        }
    }

    #[inline]
    pub(crate) fn advance(&mut self, loud_t: f64) -> f64 {
        if self.has_prev {
            let delta = (loud_t - self.prev) / LP_ITER as f64;
            for k in 1..LP_ITER {
                let ui = self.prev + delta * k as f64;
                self.y_fast = self.bf.0 * ui + self.bf.1 * self.y_fast;
                self.y_slow = self.bs.0 * ui + self.bs.1 * self.y_slow;
            }
        }
        self.y_fast = self.bf.0 * loud_t + self.bf.1 * self.y_fast;
        self.y_slow = self.bs.0 * loud_t + self.bs.1 * self.y_slow;
        self.prev = loud_t;
        self.has_prev = true;
        0.47 * self.y_fast + 0.53 * self.y_slow
    }
}

/// Duration-dependent loudness perception: 0.47*LP(3.5ms) + 0.53*LP(70ms).
pub fn temporal_weighting(loudness: &[f64]) -> Vec<f64> {
    let mut state = TwState::new();
    loudness.iter().map(|&l| state.advance(l)).collect()
}
```

**位元等價論證:** 批次幀 t 的 k=0 子步 `ui = loud[t] + delta*0`——`delta*0 == 0.0` 精確、`loud+0.0 == loud` 精確，故 k=0 等同直接用 `loud_t`。幀 t 的 k=1..23 需要 `loud[t+1]` 才能算 delta，批次在同幀內先算 delta 是因為它有整條陣列；本結構把這 23 個子步挪到 `loud[t+1]` 到達時執行，**每個 y 更新的運算元與順序逐一相同**。fast/slow 兩鏈相互獨立，兩趟掃描改單趟交錯不影響任一鏈的位元。原碼最後一幀的 k=1..23（next=0）不影響任何輸出值（無後續讀者），新碼不執行它們——輸出仍逐位相同。批次末尾語意由 flush 承接（D3）。

- [ ] **Step 2: gate（同 S2.1 Step 3）+ Commit**

```bash
git add iso532/src/zwtv/temporal_weighting.rs
git commit -m "refactor: TwState with split emission, batch tw drives it (bitwise-identical)"
```

### Task S2.6: `main_loudness_clamped`

**Files:**
- Modify: `iso532/src/core/main_loudness.rs`

- [ ] **Step 1: 失敗測試**

```rust
#[test]
fn clamped_variant_flags_and_matches_at_120() {
    let mut frame = [60.0; 28];
    frame[3] = 130.0;
    let (nm, clamped) = main_loudness_clamped(&frame, FieldType::Free);
    assert!(clamped);
    let mut at_limit = frame;
    at_limit[3] = 120.0;
    assert_eq!(nm, main_loudness(&at_limit, FieldType::Free).unwrap());
    let (_, ok) = main_loudness_clamped(&[60.0; 28], FieldType::Free);
    assert!(!ok);
}
```

- [ ] **Step 2: 抽共用主體 + 新入口**——`main_loudness` 的 16-72 行主體抽成 `fn main_loudness_unchecked(spec_third: &[f64], field: FieldType) -> [f64; 21]`（無 120 dB 檢查），`main_loudness` = 檢查後委派（公開行為與位元完全不變），再加：

```rust
/// 串流版:>120 dB 頻帶夾限到 120.0 並回報,不回 Err(P0-4)。
/// 批次 API 的錯誤語意不動。
pub fn main_loudness_clamped(spec_third: &[f64; 28], field: FieldType) -> ([f64; 21], bool) {
    let mut frame = *spec_third;
    let mut clamped = false;
    for level in frame[..11].iter_mut() {
        if *level > 120.0 {
            *level = 120.0;
            clamped = true;
        }
    }
    (main_loudness_unchecked(&frame, field), clamped)
}
```

- [ ] **Step 3: PASS + gate（golden 不變——純抽取）+ Commit**

```bash
git add iso532/src/core/main_loudness.rs
git commit -m "feat: main_loudness_clamped for stream path (P0-4), shared body extraction"
```

---

# Phase S3：ZeroState 參考路徑 + 收斂測試

### Task S3.1: `zwtv_reference_zerostate`

**Files:**
- Modify: `iso532/src/zwtv/stream.rs`

- [ ] **Step 1: 實作（`#[doc(hidden)] pub`——integration test 要用，不進文件）**

```rust
/// 測試專用:與 ZwtvStream 相同數值配方(zero-init nl、clamped main_loudness、
/// n_only、尾幀 next=0)的批次形驅動。串流等價測試(E2)的比較基準。
/// 與正式批次的唯一差異:nl 初始 (0,0) 而非 mosqito wraparound。
/// 呼叫端負責 DenormalGuard 作用域(D2)。
#[doc(hidden)]
pub fn zwtv_reference_zerostate(signal: &[f64], field: FieldType) -> Vec<f64> {
    use crate::core::calc_slopes::calc_slopes_n_only;
    use crate::core::main_loudness::main_loudness_clamped;
    use crate::zwtv::nonlinear_decay::{nl_coeffs, NlBandState};
    use crate::zwtv::temporal_weighting::TwState;
    use crate::zwtv::third_octave_levels::DEC_FACTOR;

    let n_time = signal.len().div_ceil(DEC_FACTOR);
    // tol:與批次同 kernel 選擇(use_avx2 自動),ParMode::Sequential
    let (tol, _) =
        crate::zwtv::third_octave_levels::third_octave_levels_with_mode(
            signal,
            crate::zwtv::ParMode::Sequential,
        );
    let b = nl_coeffs();
    let mut nl_state: [NlBandState; 21] = Default::default();
    let mut tw = TwState::new();
    let mut out = Vec::with_capacity(n_time.div_ceil(crate::zwtv::OUT_DECIM));

    let mut core_rows = vec![[0.0f64; 21]; n_time];
    for t in 0..n_time {
        let mut frame = [0.0f64; 28];
        for band in 0..28 {
            frame[band] = tol[band * n_time + t];
        }
        let (nm, _) = main_loudness_clamped(&frame, field);
        core_rows[t] = nm;
    }
    for t in 0..n_time {
        let next = if t + 1 < n_time {
            core_rows[t + 1]
        } else {
            [0.0; 21]
        };
        let mut nl_frame = [0.0f64; 21];
        for band in 0..21 {
            nl_frame[band] =
                nl_state[band].advance_frame(core_rows[t][band], next[band], &b);
        }
        let loud = calc_slopes_n_only(&nl_frame);
        let n = tw.advance(loud);
        if t % crate::zwtv::OUT_DECIM == 0 {
            out.push(n);
        }
    }
    out
}
```

**注意:** 參考路徑的 nl 用 **scalar** `NlBandState` 而 tol 用自動 kernel——串流本體（S4）必須同構（tol 依 use_avx2、nl 亦依 use_avx2 分群）。**為了 E2 成立，S4 實作後把本函式的 nl 段改為與串流相同的 kernel 選擇**（S4.2 的步驟裡有此項）；本 task 先以 scalar 落地讓收斂測試可跑。

- [ ] **Step 2: 可見性配套**——`NlBandState`、`TwState`、`nl_coeffs`、`main_loudness_clamped`、`calc_slopes_n_only` 需要 `pub(crate)` 或已是 pub；`OUT_DECIM` 維持 `pub(crate)`。

- [ ] **Step 3: `cargo test`（不新增斷言,先確保能編）+ Commit**

```bash
git add iso532/src/zwtv/stream.rs iso532/src/zwtv/mod.rs
git commit -m "test: ZeroState reference pipeline for stream equivalence (E2 baseline)"
```

### Task S3.2: N_warmup 收斂測試（E3 前半）

**Files:**
- Create: `iso532/tests/stream.rs`

- [ ] **Step 1: 寫測試**

```rust
mod common;
use iso532::FieldType;

/// D1:N_WARMUP_FRAMES = ceil((8*0.075 + 8*0.070) / 0.002) = 580。
const N_WARMUP_FRAMES: usize = 580;

#[test]
fn zerostate_converges_to_golden_batch_after_warmup() {
    let signal = common::synth_signal(); // 3 秒以上;若 common 的版本不足 3 秒,在本測試內以同公式生成 args 加長版
    let golden = iso532::loudness_zwtv(&signal, 48_000.0, FieldType::Free).unwrap();
    let zero = iso532::zwtv::stream::zwtv_reference_zerostate(&signal, FieldType::Free);
    assert_eq!(golden.n.len(), zero.len());
    let mut first_bitwise_equal = None;
    for (i, (g, z)) in golden.n.iter().zip(&zero).enumerate() {
        if i >= N_WARMUP_FRAMES {
            assert!(
                (g - z).abs() <= 1e-9,
                "frame {i}: golden {g} vs zerostate {z}"
            );
        }
        if first_bitwise_equal.is_none() && g.to_bits() == z.to_bits() {
            first_bitwise_equal = Some(i);
        }
    }
    println!("first bitwise-equal frame: {first_bitwise_equal:?}");
}
```

（訊號長度:`synth_signal` 現為 1 秒（48 000 樣本 → 500 幀）不足以覆蓋 580+ 餘裕——本測試內以相同公式生成 3 秒版本，勿改 common 的凍結版本。）

- [ ] **Step 2: RED→GREEN**——實測 363 幀後仍超 1e-9，查明為原 5τ+5τ 推導不足；未放大容差，改採 580 幀並保留量測證據。

- [ ] **Step 3: Commit**

```bash
git add iso532/tests/stream.rs
git commit -m "test: ZeroState-vs-golden warmup convergence gate (N_WARMUP=580, atol 1e-9)"
```

---

# Phase S4：ZwtvStream 本體

### Task S4.1: 結構、new/reset/latency/max_frames + DenormalGuard

**Files:**
- Modify: `iso532/src/zwtv/stream.rs`

- [ ] **Step 1: 失敗測試（加進 `iso532/tests/stream.rs`）**

```rust
#[test]
fn stream_constants_and_reset() {
    assert_eq!(iso532::ZwtvStream::latency_samples(), 24);
    assert!(iso532::ZwtvStream::max_frames_for_chunk(4800) >= 4800 / 96);
    let mut s = iso532::ZwtvStream::new(FieldType::Free);
    s.reset(); // 不 panic 即可,語意由 S4.3 的 chunk 測試看守
}
```

- [ ] **Step 2: 實作骨架**

```rust
use crate::core::calc_slopes::calc_slopes_n_only;
use crate::core::main_loudness::main_loudness_clamped;
use crate::sone2phon::sone2phon;
use crate::zwtv::nonlinear_decay::{nl_coeffs, NlBandState};
use crate::zwtv::temporal_weighting::TwState;
use crate::zwtv::third_octave_levels::{intensity_to_db, TolBandState, DEC_FACTOR};
use crate::zwtv::OUT_DECIM;
use crate::FieldType;

/// D1 修正推導:8·τ_var(75 ms) + 8·τ_slow(70 ms) = 1160 ms / 2 ms = 580 輸出幀。
pub const N_WARMUP_FRAMES: u64 = 580;

/// MXCSR FTZ|DAZ RAII guard(D2)。作用於本執行緒全部 SSE/AVX f64 運算;
/// Drop(含 unwind)還原原值——絕不可提前 return 洩漏設定。
#[cfg(target_arch = "x86_64")]
struct DenormalGuard {
    saved: u32,
}

#[cfg(target_arch = "x86_64")]
impl DenormalGuard {
    fn new() -> Self {
        // SAFETY: MXCSR 讀寫在 x86_64 恆安全。
        let saved = unsafe { std::arch::x86_64::_mm_getcsr() };
        unsafe { std::arch::x86_64::_mm_setcsr(saved | 0x8040) };
        Self { saved }
    }
}

#[cfg(target_arch = "x86_64")]
impl Drop for DenormalGuard {
    fn drop(&mut self) {
        // SAFETY: 還原進入時讀到的值。
        unsafe { std::arch::x86_64::_mm_setcsr(self.saved) };
    }
}

#[cfg(not(target_arch = "x86_64"))]
struct DenormalGuard;
#[cfg(not(target_arch = "x86_64"))]
impl DenormalGuard {
    fn new() -> Self {
        // TODO(R7): aarch64 以 FPCR FZ bit 實作對應 guard。
        DenormalGuard
    }
}

enum TolStage {
    Scalar(Box<[TolBandState; 28]>),
    #[cfg(target_arch = "x86_64")]
    Avx2(Box<[super::third_octave_levels::TolGroupState; 7]>),
}

enum NlStage {
    Scalar([NlBandState; 21]),
    #[cfg(target_arch = "x86_64")]
    Avx2 {
        groups: [super::nonlinear_decay::NlGroupState; 5],
        consts: super::nonlinear_decay::NlConsts,
        tail: NlBandState,
    },
}

/// 48 kHz 即時串流 zwtv。無配置 push、無 rayon、延遲 24 樣本(1 內部幀)。
/// 數值契約:與 `zwtv_reference_zerostate` 逐位一致(E2);與批次 golden
/// 的差異僅前 `N_WARMUP_FRAMES` 幀(E3)。不驗最短長度、不收 fs(D7)。
pub struct ZwtvStream {
    field: FieldType,
    tol: TolStage,
    nl_b: [f64; 6],
    nl: NlStage,
    tw: TwState,
    held_core: [f64; 21],
    has_held: bool,
    sample_phase: usize, // 0..DEC_FACTOR
    t_internal: u64,     // 下一個由 tol 產生的內部幀序號
    pending: FrameFlags,
}
```

`new(field)`：依 `crate::simd::use_avx2()` 建 `TolStage`/`NlStage`（scalar 臂 28 個 `TolBandState::new(band)` / 21 個 default；avx2 臂 7 個 `TolGroupState::new(v)` / 5 群 + tail）。`reset()`：整組重建（欄位逐一歸零等價但重建最不易漏）。`latency_samples()`/`max_frames_for_chunk`：

```rust
    pub const fn latency_samples() -> usize {
        DEC_FACTOR
    }

    /// push(chunk) 可能發射的 StreamFrame 數上界(呼叫端配置 out 用)。
    pub const fn max_frames_for_chunk(chunk_len: usize) -> usize {
        chunk_len / (DEC_FACTOR * OUT_DECIM) + 2
    }
```

- [ ] **Step 3: 編譯過、測試綠、Commit**

```bash
git add iso532/src/zwtv/stream.rs iso532/src/lib.rs iso532/tests/stream.rs
git commit -m "feat: ZwtvStream skeleton, DenormalGuard, constants"
```

### Task S4.2: push/flush 核心迴圈

**Files:**
- Modify: `iso532/src/zwtv/stream.rs`

- [ ] **Step 1: 先寫最強測試（主計畫風險 #4 的 TDD 順序強制:先有「單 push 全訊號 == ZeroState 參考」再動內插碼）**

```rust
#[test]
fn single_push_whole_signal_matches_zerostate_reference() {
    let signal = common::synth_signal();
    let reference = iso532::zwtv::stream::zwtv_reference_zerostate(&signal, FieldType::Free);
    let mut stream = iso532::ZwtvStream::new(FieldType::Free);
    let mut out = vec![iso532::StreamFrame::default(); signal.len() / 96 + 4];
    let mut got = Vec::new();
    let n = stream.push(&signal, &mut out);
    got.extend_from_slice(&out[..n]);
    let n = stream.flush(&mut out);
    got.extend_from_slice(&out[..n]);
    assert_eq!(got.len(), reference.len());
    for (i, (f, r)) in got.iter().zip(&reference).enumerate() {
        assert_eq!(f.n.to_bits(), r.to_bits(), "frame {i}");
        assert_eq!(f.t_frame_index, i as u64);
        assert_eq!(f.n_phon.to_bits(), iso532::sone2phon(f.n).to_bits());
    }
}
```

**同 task 前置:** 參考路徑此時仍在無 guard 環境生成——把 `zwtv_reference_zerostate` 函式體整體包進 `DenormalGuard::new()` 作用域（函式開頭 `let _guard = DenormalGuard::new();`），並把 nl 段的 kernel 選擇改為與串流一致（`use_avx2()` 時走 5 群 `NlGroupState` + tail scalar，否則 21 個 `NlBandState`）——D2/E2 的兩側同構就此成立。

- [ ] **Step 2: RED 確認後實作 push/flush**

```rust
    /// 餵入任意長度 chunk;每完成一個 2 ms 輸出幀寫入 `out` 一格。
    /// 回傳寫入幀數。`out.len() < max_frames_for_chunk(chunk.len())` 屬
    /// 呼叫端錯誤(debug_assert)。零配置、無 rayon(有測試看守)。
    pub fn push(&mut self, chunk: &[f64], out: &mut [StreamFrame]) -> usize {
        debug_assert!(out.len() >= Self::max_frames_for_chunk(chunk.len()));
        let _guard = DenormalGuard::new();
        let mut written = 0usize;
        for &raw in chunk {
            let sample = if raw.is_finite() {
                raw
            } else {
                self.pending.insert(FrameFlags::NONFINITE_INPUT);
                0.0
            };
            let emit_tol = self.sample_phase == 0;
            let tol_frame = self.advance_tol(sample, emit_tol);
            self.sample_phase = (self.sample_phase + 1) % DEC_FACTOR;
            if let Some(frame) = tol_frame {
                written += self.on_internal_frame(frame, out, written);
            }
        }
        written
    }

    /// 排空 lookahead 尾幀(next=0 語意,D3)。之後僅 reset/new 可再用。
    pub fn flush(&mut self, out: &mut [StreamFrame]) -> usize {
        debug_assert!(!out.is_empty());
        let _guard = DenormalGuard::new();
        if !self.has_held {
            return 0;
        }
        self.has_held = false;
        let held = self.held_core;
        self.emit_loudness(&held, &[0.0; 21], out, 0)
    }

    /// tol 一樣本推進;`emit` 時回傳 28 帶 dB 幀。
    fn advance_tol(&mut self, sample: f64, emit: bool) -> Option<[f64; 28]> { ... }

    /// 收到內部幀 t = self.t_internal:main_loudness → nl 持有邏輯。
    fn on_internal_frame(
        &mut self,
        tol_db: [f64; 28],
        out: &mut [StreamFrame],
        written: usize,
    ) -> usize {
        let (core, clamped) = main_loudness_clamped(&tol_db, self.field);
        if clamped {
            self.pending.insert(FrameFlags::CLAMPED_120DB);
        }
        let mut wrote = 0;
        if self.has_held {
            let held = self.held_core;
            wrote = self.emit_loudness(&held, &core, out, written);
        }
        self.held_core = core;
        self.has_held = true;
        self.t_internal += 1;
        wrote
    }

    /// nl(幀 i = t_internal-1,拆 held/next)→ calc_slopes → tw → 抽取發射。
    fn emit_loudness(
        &mut self,
        held: &[f64; 21],
        next: &[f64; 21],
        out: &mut [StreamFrame],
        written: usize,
    ) -> usize {
        let nl_frame = self.advance_nl(held, next);
        let loud = calc_slopes_n_only(&nl_frame);
        let n = self.tw.advance(loud);
        let i = self.t_internal - u64::from(self.has_held); // 發射的內部幀序號 = 已產生數-1;實作時直接維護獨立計數器更清楚,見下
        ...
    }
```

**實作備註（非選配）:**
- 內部幀序號記帳:維護 `emitted_internal: u64`（已發射的內部幀數）比從 `t_internal` 反推安全——`emit_loudness` 內 `let i = self.emitted_internal; self.emitted_internal += 1;`，發射條件 `i % OUT_DECIM as u64 == 0`，StreamFrame `t_frame_index = i / OUT_DECIM as u64`，flags `let mut flags = self.pending.take(); if t_frame_index < N_WARMUP_FRAMES { flags.insert(FrameFlags::WARMUP); }`。
- `advance_tol` scalar 臂:28 個 state 逐一 `advance(sample)`；`emit` 時 `intensity_to_db` 進 `[f64;28]`。AVX2 臂:7 群 `advance`，emit 時 storeu lanes → dB。**AVX2 臂的 state.advance 是 `#[target_feature]` fn,呼叫點需 `unsafe` + 建構時已驗 use_avx2 的 SAFETY 註解。**
- `advance_nl` scalar 臂:21 帶逐一 `advance_frame(held[b], next[b], &self.nl_b)`。AVX2 臂:5 群 `_mm256_loadu_pd(&held[4g])`/`loadu(&next[4g])` → `advance_frame` → storeu 到 `nl_frame[4g..]`；tail 帶 20 走 scalar `NlBandState`（與批次分工一致,D5）。lane 排列與批次 `nl_loudness_load4` 的 set_pd 順序等價（loadu lane0 = 低位址 = band 4g——與 set_pd(e3..e0) 的 e0=band 相同）,在程式碼註解記一句。
- push 的 `written` 上限由 debug_assert 擔保;release 下呼叫端違約是未定義行為嗎?不是——寫超界是 safe Rust 的 index panic,`out[written]` 越界會 panic 而非 UB。文件寫明。

- [ ] **Step 3: GREEN（E2 單 push 逐位)**

Run: `cd iso532 && cargo test --test stream`
Expected: 全數 PASS。scalar 路徑複驗:比照 `iso532/tests/simd_dispatch.rs` 的 FORCE_SCALAR 單測試 binary 慣例，新增 `iso532/tests/stream_scalar.rs`（單一 `#[test]`,設 FORCE_SCALAR 後跑同一組單 push 等價斷言——直接呼叫共用 helper,helper 放 `tests/common`）。

- [ ] **Step 4: Commit**

```bash
git add iso532/src/zwtv/stream.rs iso532/tests/
git commit -m "feat: ZwtvStream push/flush, bitwise-equal to ZeroState reference on both kernels"
```

### Task S4.3: chunk 尺寸不變性（驗收 1——本階段最強測試）

**Files:**
- Modify: `iso532/tests/stream.rs`

- [ ] **Step 1: 寫測試**

```rust
fn run_chunked(signal: &[f64], chunks: impl Iterator<Item = usize>) -> Vec<iso532::StreamFrame> {
    let mut stream = iso532::ZwtvStream::new(FieldType::Free);
    let mut out = vec![iso532::StreamFrame::default(); iso532::ZwtvStream::max_frames_for_chunk(signal.len())];
    let mut got = Vec::new();
    let mut pos = 0;
    for c in chunks {
        if pos >= signal.len() {
            break;
        }
        let end = (pos + c).min(signal.len());
        let n = stream.push(&signal[pos..end], &mut out);
        got.extend_from_slice(&out[..n]);
        pos = end;
    }
    while pos < signal.len() {
        let end = (pos + 480).min(signal.len());
        let n = stream.push(&signal[pos..end], &mut out);
        got.extend_from_slice(&out[..n]);
        pos = end;
    }
    let n = stream.flush(&mut out);
    got.extend_from_slice(&out[..n]);
    got
}

#[test]
fn chunk_size_invariance_bitwise() {
    let signal = common::synth_signal();
    let baseline = run_chunked(&signal, std::iter::repeat(signal.len()));
    for &c in &[1usize, 7, 24, 64, 480, 4096] {
        let got = run_chunked(&signal, std::iter::repeat(c));
        assert_eq!(got.len(), baseline.len(), "chunk={c}");
        for (i, (a, b)) in got.iter().zip(&baseline).enumerate() {
            assert_eq!(a.n.to_bits(), b.n.to_bits(), "chunk={c} frame={i}");
            assert_eq!(a.t_frame_index, b.t_frame_index, "chunk={c} frame={i}");
            assert_eq!(a.flags, b.flags, "chunk={c} frame={i}");
        }
    }
    // 決定性偽隨機 chunk 序列(不用 rand 依賴;LCG 播種寫死)
    let mut lcg: u64 = 0x9E3779B97F4A7C15;
    let rand_chunks = std::iter::from_fn(move || {
        lcg = lcg.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
        Some(1 + (lcg >> 33) as usize % 997)
    });
    let got = run_chunked(&signal, rand_chunks.take(10_000));
    assert_eq!(got.len(), baseline.len());
    for (a, b) in got.iter().zip(&baseline) {
        assert_eq!(a.n.to_bits(), b.n.to_bits());
    }
}
```

- [ ] **Step 2: RED→修 carry/相位 bug→GREEN**（凡 chunk 邊界處理的 bug 都在此現形——修串流本體,不修測試）

- [ ] **Step 3: `reset` 語意測試順手加**（reset 後重跑 = 新建重跑,逐位相同）+ **E3 串流版**（`stream vs golden`,t≥580 atol 1e-9——把 S3.2 的比較對象換成串流輸出再跑一次,函式化避免複製貼上）+ Commit

```bash
git add iso532/tests/stream.rs
git commit -m "test: chunk-size invariance (bitwise), reset semantics, stream-vs-golden warmup gate"
```

### Task S4.4: P0-2/P0-4 行為測試（NaN 不毒化、120 dB 不中斷）

**Files:**
- Modify: `iso532/tests/stream.rs`

- [ ] **Step 1: 寫測試**

```rust
#[test]
fn nonfinite_input_flags_and_recovers() {
    let signal = common::synth_signal();
    let mut dirty = signal.clone();
    for v in dirty[4800..4848].iter_mut() {
        *v = f64::NAN;
    }
    let clean_frames = run_chunked(&signal, std::iter::repeat(480));
    let dirty_frames = run_chunked(&dirty, std::iter::repeat(480));
    // NaN 落點所屬的發射幀帶 flag
    assert!(dirty_frames.iter().any(|f| f.flags.contains(iso532::FrameFlags::NONFINITE_INPUT)));
    // 全程有限
    assert!(dirty_frames.iter().all(|f| f.n.is_finite()));
    // 注入點 1 秒後輸出回到與乾淨串流一致(狀態未毒化;NaN 置 0 造成的
    // 暫態以最慢時間常數衰減,1 秒 >> 5τ_max=375 ms)
    for (a, b) in clean_frames.iter().zip(&dirty_frames).skip(4800 / 96 + 500) {
        assert!((a.n - b.n).abs() < 1e-9);
    }
}

#[test]
fn clamp_120db_flags_and_continues() {
    // 130 dB 量級低頻:0.02 換算遠超 120 dB SPL 的振幅——用足以觸發
    // main_loudness 夾限的正弦(振幅 90,任意大聲即可)
    let mut signal = common::synth_signal();
    for (i, v) in signal[9600..14400].iter_mut().enumerate() {
        *v = 90.0 * (2.0 * std::f64::consts::PI * 100.0 * i as f64 / 48_000.0).sin();
    }
    let frames = run_chunked(&signal, std::iter::repeat(480));
    assert!(frames.iter().any(|f| f.flags.contains(iso532::FrameFlags::CLAMPED_120DB)));
    assert!(frames.iter().all(|f| f.n.is_finite()));
    // 批次對同訊號回 Err——串流不中斷即是 P0-4 的驗收
    assert!(iso532::loudness_zwtv(&signal, 48_000.0, FieldType::Free).is_err());
}
```

- [ ] **Step 2: RED→GREEN→Commit**

```bash
git add iso532/tests/stream.rs
git commit -m "test: P0-2 NaN poison recovery, P0-4 120dB clamp-and-continue"
```

---

# Phase S5：P0-1 denormal 看守 + MXCSR 洩漏測試

### Task S5.1: MXCSR 還原測試（主計畫風險 #1）

**Files:**
- Modify: `iso532/tests/stream.rs`

- [ ] **Step 1: 寫測試**

```rust
#[cfg(target_arch = "x86_64")]
#[test]
fn push_restores_mxcsr() {
    let before = unsafe { std::arch::x86_64::_mm_getcsr() };
    let mut s = iso532::ZwtvStream::new(FieldType::Free);
    let mut out = vec![iso532::StreamFrame::default(); 64];
    let chunk = vec![0.001f64; 4800];
    s.push(&chunk, &mut out);
    assert_eq!(unsafe { std::arch::x86_64::_mm_getcsr() }, before);
    s.flush(&mut out);
    assert_eq!(unsafe { std::arch::x86_64::_mm_getcsr() }, before);
}
```

- [ ] **Step 2: GREEN 應直接通過（RAII 已在 S4.1）;若紅,查提前 return 路徑。Commit**

```bash
git add iso532/tests/stream.rs
git commit -m "test: MXCSR restored after push/flush (P0-1 leak guard)"
```

### Task S5.2: 靜音吞吐測試（P0-1 驗收,local-only）

**Files:**
- Modify: `iso532/tests/stream.rs`

- [ ] **Step 1: 寫 `#[ignore]` 測試（計時類,CI 不跑,SOP 記錄本機跑）**

```rust
/// P0-1 驗收:60 s 靜音 vs 60 s 正弦吞吐劣化 < 20%(denormal 已被 FTZ 消滅)。
/// 計時測試,本機手動:cargo test --release --test stream silence -- --ignored --nocapture
#[test]
#[ignore]
fn silence_throughput_within_20pct_of_sine() {
    let sine: Vec<f64> = (0..48_000 * 60)
        .map(|i| (2.0 * std::f64::consts::PI * 1000.0 * i as f64 / 48_000.0).sin() * 0.02)
        .collect();
    let silence = vec![0.0f64; 48_000 * 60];
    let time = |sig: &[f64]| {
        let mut s = iso532::ZwtvStream::new(FieldType::Free);
        let mut out = vec![iso532::StreamFrame::default(); 64];
        let t0 = std::time::Instant::now();
        for c in sig.chunks(480) {
            s.push(c, &mut out);
        }
        t0.elapsed()
    };
    let t_sine = time(&sine);
    let t_sil = time(&silence);
    println!("sine {t_sine:?} silence {t_sil:?}");
    assert!(t_sil.as_secs_f64() < t_sine.as_secs_f64() * 1.2);
}
```

- [ ] **Step 2: 本機 `--release -- --ignored` 跑過並記錄數字。Commit**

```bash
git add iso532/tests/stream.rs
git commit -m "test: silence-vs-sine throughput gate for denormal protection (local, ignored)"
```

---

# Phase S6：零配置、無 rayon、效能

### Task S6.1: counting allocator 零配置證明（驗收 3）

**Files:**
- Create: `iso532/tests/stream_alloc.rs`（獨立 binary——global allocator 是 per-binary 的）

- [ ] **Step 1: 寫測試**

```rust
//! 驗收 3:push/flush 路徑 0 allocation。counting allocator 是 binary 級
//! 全域資源,本檔只放這一個測試。
use std::alloc::{GlobalAlloc, Layout, System};
use std::sync::atomic::{AtomicU64, Ordering};

struct Counting;
static ALLOCS: AtomicU64 = AtomicU64::new(0);

unsafe impl GlobalAlloc for Counting {
    unsafe fn alloc(&self, l: Layout) -> *mut u8 {
        ALLOCS.fetch_add(1, Ordering::Relaxed);
        unsafe { System.alloc(l) }
    }
    unsafe fn dealloc(&self, p: *mut u8, l: Layout) {
        unsafe { System.dealloc(p, l) }
    }
}

#[global_allocator]
static A: Counting = Counting;

#[test]
fn push_and_flush_do_not_allocate() {
    let signal: Vec<f64> = (0..48_000)
        .map(|i| (2.0 * std::f64::consts::PI * 1000.0 * i as f64 / 48_000.0).sin() * 0.02)
        .collect();
    let mut s = iso532::ZwtvStream::new(iso532::FieldType::Free);
    let mut out = vec![iso532::StreamFrame::default(); 64];
    let before = ALLOCS.load(Ordering::Relaxed);
    for c in signal.chunks(480) {
        s.push(c, &mut out);
    }
    s.flush(&mut out);
    assert_eq!(ALLOCS.load(Ordering::Relaxed), before, "push/flush allocated");
}
```

- [ ] **Step 2: RED（若 Box/Vec 混進 push 路徑）→修→GREEN→Commit**

```bash
git add iso532/tests/stream_alloc.rs
git commit -m "test: zero-allocation proof for stream push/flush (counting allocator)"
```

### Task S6.2: 無 rayon 證明（驗收 4）

**Files:**
- Create: `iso532/tests/stream_no_rayon.rs`（獨立 binary——全域 pool 是行程級資源）

- [ ] **Step 1: 寫測試**

```rust
//! 驗收 4:串流路徑不觸發 rayon 全域 pool 建立。原理:build_global()
//! 在 pool 已存在時回 Err——若串流動過 rayon,本斷言就紅。
//! 全域 pool 是行程級資源,本檔只放這一個測試。

#[test]
fn stream_does_not_initialize_rayon_pool() {
    let signal = vec![0.001f64; 48_000];
    let mut s = iso532::ZwtvStream::new(iso532::FieldType::Free);
    let mut out = vec![iso532::StreamFrame::default(); 64];
    for c in signal.chunks(480) {
        s.push(c, &mut out);
    }
    s.flush(&mut out);
    assert!(
        rayon::ThreadPoolBuilder::new().num_threads(1).build_global().is_ok(),
        "rayon global pool was initialized by the stream path"
    );
}
```

（`iso532` 的 dev-dependencies 已含 rayon 於正式依賴——測試直接 `use rayon` 即可。）

- [ ] **Step 2: GREEN→Commit**

```bash
git add iso532/tests/stream_no_rayon.rs
git commit -m "test: stream path never builds the rayon pool"
```

### Task S6.3: criterion 基準 + 驗收 5 記錄

**Files:**
- Modify: 既有 bench 檔（`iso532/benches/` 下與 `zwtv_10s` 同檔）

- [ ] **Step 1: 加 bench**

```rust
fn stream_push_10s(c: &mut Criterion) {
    let signal: Vec<f64> = (0..48_000 * 10)
        .map(|i| (2.0 * std::f64::consts::PI * 1000.0 * i as f64 / 48_000.0).sin() * 0.02)
        .collect();
    c.bench_function("stream_push_10s_480chunk", |b| {
        b.iter(|| {
            let mut s = iso532::ZwtvStream::new(iso532::FieldType::Free);
            let mut out = vec![iso532::StreamFrame::default(); 64];
            for chunk in signal.chunks(480) {
                black_box(s.push(chunk, &mut out));
            }
            s.flush(&mut out)
        })
    });
}
```

- [ ] **Step 2: 本機量測換算單幀成本**——10 s = 5000 輸出幀；總時間/5000 = 每幀 µs。**驗收:AVX2 ≤ 60 µs;scalar 記錄實測（預算 ≤200 µs）**。量測遵守主計畫 X2:機器閒置、同日同機。數字回填主計畫 §R5 與本文件末尾的審查紀錄區。

- [ ] **Step 3: Commit**

```bash
git add iso532/benches/
git commit -m "bench: stream_push_10s; record per-frame cost vs 60us budget"
```

---

# Phase S7：C-ABI 串流擴充 + v1 凍結 + 文件

### Task S7.1: `iso532_stream_*`

**Files:**
- Modify: `iso532-ffi/src/lib.rs`
- Test: `iso532-ffi/tests/ffi.rs`

- [ ] **Step 1: 失敗測試（ffi.rs 追加）**

```rust
#[test]
fn stream_matches_rust_stream_bitwise() {
    let signal = quiet_signal(48_000);
    // Rust 端
    let mut rs = iso532::ZwtvStream::new(iso532::FieldType::Free);
    let mut rout = vec![iso532::StreamFrame::default(); 64];
    let mut rust_frames = Vec::new();
    for c in signal.chunks(480) {
        let n = rs.push(c, &mut rout);
        rust_frames.extend_from_slice(&rout[..n]);
    }
    let n = rs.flush(&mut rout);
    rust_frames.extend_from_slice(&rout[..n]);
    // C 端
    let h = unsafe { iso532_stream_new(ISO532_FIELD_FREE) };
    assert!(!h.is_null());
    let mut cout = vec![Iso532StreamFrame::default(); 64];
    let mut c_frames: Vec<Iso532StreamFrame> = Vec::new();
    for c in signal.chunks(480) {
        let mut written = 0usize;
        let code = unsafe {
            iso532_stream_push(h, c.as_ptr(), c.len(), cout.as_mut_ptr(), cout.len(), &mut written)
        };
        assert_eq!(code, ISO532_OK);
        c_frames.extend_from_slice(&cout[..written]);
    }
    let mut written = 0usize;
    assert_eq!(
        unsafe { iso532_stream_flush(h, cout.as_mut_ptr(), cout.len(), &mut written) },
        ISO532_OK
    );
    c_frames.extend_from_slice(&cout[..written]);
    unsafe { iso532_stream_free(h) };
    assert_eq!(rust_frames.len(), c_frames.len());
    for (r, c) in rust_frames.iter().zip(&c_frames) {
        assert_eq!(r.n.to_bits(), c.n.to_bits());
        assert_eq!(r.t_frame_index, c.t_frame_index);
        assert_eq!(r.flags.bits(), c.flags);
    }
}

#[test]
fn stream_new_rejects_invalid_field_and_null_paths() {
    assert!(unsafe { iso532_stream_new(2) }.is_null());
    let mut written = 1usize;
    let code = unsafe {
        iso532_stream_push(std::ptr::null_mut(), std::ptr::null(), 0, std::ptr::null_mut(), 0, &mut written)
    };
    assert_eq!(code, ISO532_ERR_NULL_POINTER);
    assert_eq!(written, 0);
}
```

- [ ] **Step 2: 實作**

```rust
/// 串流輸出幀(與 iso532::StreamFrame 佈局相同;32 bytes)。
#[repr(C)]
#[derive(Clone, Copy, Debug, Default)]
pub struct Iso532StreamFrame {
    pub t_frame_index: u64,
    pub n: f64,
    pub n_phon: f64,
    /// FrameFlags bits: 1=CLAMPED_120DB, 2=NONFINITE_INPUT, 4=WARMUP。
    pub flags: u32,
    pub _reserved: u32,
}

/// Opaque 串流 handle。iso532_stream_new 配置、iso532_stream_free 釋放;
/// 同一 handle 不得跨執行緒並行呼叫(無內部鎖)。
pub struct Iso532Stream {
    inner: iso532::ZwtvStream,
}

/// 建立 48 kHz 串流。field_type 非法回傳 NULL。延遲 24 樣本。
#[no_mangle]
pub extern "C" fn iso532_stream_new(field_type: i32) -> *mut Iso532Stream {
    let Ok(field) = iso532::FieldType::try_from(field_type) else {
        return std::ptr::null_mut();
    };
    match catch_unwind(|| {
        Box::into_raw(Box::new(Iso532Stream {
            inner: iso532::ZwtvStream::new(field),
        }))
    }) {
        Ok(p) => p,
        Err(_) => std::ptr::null_mut(),
    }
}

/// push chunk。out 至少 iso532_stream_max_frames(chunk_len) 格;實寫幀數
/// 經 out_written 回報。錯誤碼同批次;panic 回 -2 後 handle 視為毒化,
/// 僅 iso532_stream_free 合法。
///
/// # Safety
/// handle 來自 iso532_stream_new 且未 free;chunk 可讀 chunk_len 個 f64;
/// out 可寫 out_cap 個 Iso532StreamFrame;out_written 可寫。
#[no_mangle]
pub unsafe extern "C" fn iso532_stream_push(
    handle: *mut Iso532Stream,
    chunk: *const f64,
    chunk_len: usize,
    out: *mut Iso532StreamFrame,
    out_cap: usize,
    out_written: *mut usize,
) -> i32 {
    guarded(|| {
        if out_written.is_null() {
            return ISO532_ERR_NULL_POINTER;
        }
        // SAFETY: 上一行已驗非空。
        unsafe { *out_written = 0 };
        if handle.is_null() || (chunk.is_null() && chunk_len > 0) || out.is_null() {
            return ISO532_ERR_NULL_POINTER;
        }
        if out_cap < iso532::ZwtvStream::max_frames_for_chunk(chunk_len) {
            return ISO532_ERR_INTERNAL; // 呼叫端緩衝不足:拒收,不部分寫入
        }
        // SAFETY: 呼叫端契約(見 Safety 註解)。
        let (stream, chunk_s) = unsafe {
            (&mut (*handle).inner, std::slice::from_raw_parts(chunk, chunk_len))
        };
        // StreamFrame 與 Iso532StreamFrame repr(C) 同佈局(有測試釘住)
        let out_s = unsafe {
            std::slice::from_raw_parts_mut(out as *mut iso532::StreamFrame, out_cap)
        };
        let n = stream.push(chunk_s, out_s);
        // SAFETY: 已驗非空。
        unsafe { *out_written = n };
        ISO532_OK
    })
}
```

`iso532_stream_flush`（同形，cap ≥ 1）、`iso532_stream_free`（`drop(Box::from_raw)`,null 容忍）、`iso532_stream_max_frames(chunk_len) -> usize`（轉發）。**佈局互鎖測試**：`assert_eq!(size_of::<Iso532StreamFrame>(), size_of::<iso532::StreamFrame>())` + offset 逐欄（`std::mem::offset_of!`）。

- [ ] **Step 3: GREEN + panic 注入既有機制驗 push 路徑（test-panic feature 加一個 stream 版）+ Commit**

```bash
git add iso532-ffi/src/ iso532-ffi/tests/
git commit -m "feat: iso532_stream_* C ABI (opaque handle, caller-allocated frames)"
```

### Task S7.2: header 重生 + v1 凍結

**Files:**
- Modify: `iso532-ffi/cbindgen.toml`（若 opaque type 需要 export 設定）、`iso532-ffi/include/iso532.h`（重生）
- Modify: `iso532-ffi/tests/smoke.c`（加串流 smoke 段:new→push 正弦→flush→free,印前 3 幀）

- [ ] **Step 1: `cbindgen --config cbindgen.toml --crate iso532-ffi --output include/iso532.h`（0.29.4,見 skill）；檢視 diff:新增 `Iso532Stream`(opaque)/`Iso532StreamFrame`/5 函式/flag 常數。header 頂端版本註解由 `/* v0, pre-1.0: may change */` 改為 v1 凍結宣告（批次 + 串流介面自此不變;此行在 cbindgen.toml 的 header 前言設定裡改）。**

- [ ] **Step 2: smoke.c 串流段 + 本機無 C 編譯器則標記 CI 驗證（與 R3 慣例同）。Commit**

```bash
git add iso532-ffi/
git commit -m "feat: regenerate header, freeze C ABI v1 (batch + stream)"
```

### Task S7.3: 文件收尾

**Files:**
- Modify: `docs/superpowers/plans/2026-07-05-roadmap-master-plan.md`（§R5 回填:實測效能、N_warmup=580 修正推導、D1–D7 決策連結、X3 的 v1 凍結完成註記）
- Modify: `.codex/skills/iso532-r3-verification/SKILL.md`（步驟 3 加 `--test stream --test stream_alloc --test stream_no_rayon`;或建 R5 版 skill——實作者擇一並記錄）

- [ ] **Step 1: 回填 + Commit**

```bash
git add docs/ .codex/
git commit -m "docs: R5 closeout — measured numbers, warmup derivation, v1 freeze recorded"
```

---

## 實作紀錄（2026-07-16）

- S0–S7 原始碼已落地：狀態化 tol/nl/tw、ZwtvStream、sone2phon、P0 flags/FTZ、零配置/無 Rayon測試、criterion、C ABI opaque handle 與 v1 header。
- 批次凍結契約：四組 R1 n/spec/time hash 逐字不變；Rust stream tests 8 passed + 1 ignored local timing，另有 scalar、allocation、no-rayon 各 1 passed。9 組 golden 的 3 秒延長訊號逐一通過 E2 ZeroState 逐位等價與 E3 frame ≥580 的 1e-9 收斂 gate。
- Warmup 修正：原 363-frame 推導在 frame 363 的差值為 1.7133437069e-7；3 秒合成訊號第一個持續 ≤1e-9 的 frame 為 544。採 8τ_var+8τ_slow = 580 frames，保留 36-frame margin，容差維持 1e-9。
- 效能（本機 Criterion，10 s = 5000 frames）：AVX2 median 241.78 ms = 48.36 µs/frame；scalar median 355.48 ms = 71.10 µs/frame，分別通過 60/200 µs 預算。
- Python：maturin release build 成功；smoke 6/6；collection 24；ISO532_REQUIRE_PARITY=1 且 BLAS/OMP 單執行緒時 formal parity 18/18、0 skipped。
- FFI：cargo test --features test-panic 為 13/13；cbindgen 0.29.4 重生 header，包含 opaque handle、frame、5 函式與三個 flag 常數。VS 2022 x64 MSVC 本機編譯、連結、執行 C smoke 成功（frames=500，zwtv_n0=3.779000）；僅有既知 CP950 C4819 註解編碼警告。
- P0-1 local timing：原 target 的 release executable 遭 Windows 資源/鎖定問題，改用乾淨 D:/tmp target 重跑通過；60 s sine 874.54 ms、silence 442.39 ms，靜音未劣化（遠低於 +20% 上限）。

- Review closeout: `main_loudness_clamped` intentionally remains `pub(crate)` rather than the provisional plan's `pub`; the stream path can consume it without expanding the public API.
- Acceptance 6 is implemented, not descoped: the Python binding exports `sone2phon`, and smoke tests restate the two-branch formula across 0..20 sone at 0.02 increments with atol 1e-12 plus 1/2/4-sone anchors.

## Self-Review 紀錄（計畫作者已核對）

1. **主計畫驗收 6 條逐條有 task:** 1→S4.3;2→S4.2/S3.2/S4.3 Step 3;3→S6.1;4→S6.2;5→S6.3;6→S1.1。P0 1–4→S5.1/S5.2、S4.4;P1-5(配置移入狀態)→S2 全部;P1-6(單幀入口)→S2 各 advance;phon→S1.1;`iso532_stream_*`→S7;X3 v1 凍結→S7.2。
2. **型別一致性:** `advance`/`advance_frame`/`TwState::advance` 簽名在 S2 定義、S3/S4 消費處一致;`FrameFlags::bits()` S1 定義、S7 消費;`max_frames_for_chunk` S4.1 定義、S6/S7 消費。
3. **已知留白(非 placeholder,是明示的搬移指令):** S2.2 `TolGroupState::new` 與 S2.4 的函式體指明「從現行檔案逐字搬移」並給出行號——原始碼就是規格,重印徒增轉錄錯誤風險。
4. **凍結面清單:** golden 12 雜湊(S2 每步)、hash_gate、py 契約(不動)、錯誤碼表(只新增使用)、FrameFlags bits(S1 凍結測試)、`Iso532StreamFrame` 佈局(S7 互鎖測試)、header v1(S7.2)。
