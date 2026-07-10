# R3-P2:iso532-ffi(C ABI v0)Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 為 `iso532` 建立 C ABI v0(`iso532-ffi` crate + `include/iso532.h`),含 panic 邊界、錯誤碼、尺寸查詢,CI 雙平台 C smoke test 全綠。

**Architecture:** 新獨立 crate(不建 workspace,path 依賴 `../iso532`),caller-allocated 兩段式記憶體模型,每個 `extern "C"` 函式體以 `guarded()` 包 `catch_unwind`。header 由 cbindgen 生成後 commit,CI smoke test 對已 commit 的 header 編譯——簽名漂移即編譯失敗。

**Tech Stack:** Rust 2021(rustc 1.93)、cbindgen、gcc(ubuntu)/MSVC cl(windows,`ilammy/msvc-dev-cmd`)。

**Spec:** `docs/superpowers/specs/2026-07-10-r3-c-abi-python-binding-design.md` §4–§5

**Exit Gate:** CI 雙平台全綠(fmt/clippy/test 含 panic 注入與 property test + C smoke);`iso532/src/` 零 diff。

---

## 背景(給零脈絡的工程師)

- Rust API:`iso532::loudness_zwtv(&[f64], fs, FieldType) -> Result<LoudnessTimeVarying, Iso532Error>`;`LoudnessTimeVarying { n: Vec<f64>, n_specific: Vec<f64> /*240×frames, bark-major row-major*/, bark_axis: Vec<f64> /*240*/, time_axis: Vec<f64> }`。`loudness_zwst` 回 `LoudnessStationary { n: f64, n_specific: Vec<f64> /*240*/, bark_axis }`。
- `Iso532Error` 三變體:`LevelExceeds120dB`、`SignalTooShort{got,need}`(下限 4800 樣本)、`UnsupportedSampleRate(f64)`(僅收 48000.0)。
- 輸出幀數閉式解:`frames = ceil(ceil(signal_len/24)/4)`(`DEC_FACTOR=24`,calc_slopes 每 4 幀取 1)。
- 錯誤碼(spec §5,發布後不得重排):0 OK;1/2/3 = 上述三變體;-1 NULL;-2 panic;-3 field_type 非 0/1。
- **本 crate 一律不得設 `panic = "abort"`**(catch_unwind 需要 unwind)。
- 指令在 Git Bash;Rust 指令於 `iso532-ffi/` 內執行,git 於 repo 根。

### Task 0 開始前

```bash
cd /d/ISO532 && ls iso532/Cargo.toml && cargo --version
```

---

### Task 1: crate 骨架 + 失敗測試(red)

**Files:**
- Create: `iso532-ffi/Cargo.toml`
- Create: `iso532-ffi/src/lib.rs`(僅常數,函式後補)
- Create: `iso532-ffi/tests/ffi.rs`

- [ ] **Step 1: Cargo.toml**

```toml
[package]
name = "iso532-ffi"
version = "0.1.0"
edition = "2021"
description = "C ABI (v0) for the iso532 crate"
license = "Apache-2.0"

[lib]
name = "iso532_ffi"
# rlib 必須保留,否則 tests/ 連結不到本 crate
crate-type = ["cdylib", "staticlib", "rlib"]

[dependencies]
iso532 = { path = "../iso532" }
rayon = { version = "1.12", optional = true }

[features]
# 隱藏的 panic 注入匯出(不進 header、不進 release 交付)
test-panic = ["dep:rayon"]
```

- [ ] **Step 2: src/lib.rs 先只放錯誤碼常數**

```rust
//! C ABI (v0) for the `iso532` crate. Batch API only; the streaming handle
//! API arrives with R5 (`iso532_stream_*`), which also freezes v1.
//!
//! Every extern fn body is wrapped in `catch_unwind` (panic -> -2); this
//! crate must never be built with `panic = "abort"`.

pub const ISO532_OK: i32 = 0;
pub const ISO532_ERR_LEVEL_EXCEEDS_120DB: i32 = 1;
pub const ISO532_ERR_SIGNAL_TOO_SHORT: i32 = 2;
pub const ISO532_ERR_UNSUPPORTED_SAMPLE_RATE: i32 = 3;
pub const ISO532_ERR_NULL_POINTER: i32 = -1;
pub const ISO532_ERR_PANIC: i32 = -2;
pub const ISO532_ERR_INVALID_FIELD_TYPE: i32 = -3;
```

- [ ] **Step 3: tests/ffi.rs(完整測試,先寫全部)**

```rust
use iso532_ffi::*;

const FS: f64 = 48_000.0;

/// 100 Hz 鋸齒,±0.01 Pa(~54 dB SPL)——內容不重要、不觸發任何錯誤路徑,
/// 且不經 libm(property test 每輪重算,要快)。
fn quiet_signal(len: usize) -> Vec<f64> {
    (0..len)
        .map(|i| (i % 480) as f64 / 480.0 * 0.02 - 0.01)
        .collect()
}

/// 100 Hz 正弦、振幅 2000 Pa(~160 dB SPL):300 Hz 以下頻帶必超 120 dB。
fn loud_low_signal() -> Vec<f64> {
    (0..48_000)
        .map(|i| 2.0e3 * (2.0 * std::f64::consts::PI * 100.0 * i as f64 / FS).sin())
        .collect()
}

struct ZwtvOut {
    n: Vec<f64>,
    spec: Vec<f64>,
    bark: Vec<f64>,
    time: Vec<f64>,
}

fn call_zwtv(signal: &[f64], fs: f64, field: i32) -> (i32, ZwtvOut) {
    let frames = iso532_zwtv_out_frames(signal.len());
    let mut out = ZwtvOut {
        n: vec![0.0; frames],
        spec: vec![0.0; 240 * frames],
        bark: vec![0.0; 240],
        time: vec![0.0; frames],
    };
    let code = unsafe {
        iso532_loudness_zwtv(
            signal.as_ptr(),
            signal.len(),
            fs,
            field,
            out.n.as_mut_ptr(),
            out.spec.as_mut_ptr(),
            out.bark.as_mut_ptr(),
            out.time.as_mut_ptr(),
        )
    };
    (code, out)
}

#[test]
fn zwtv_happy_path_matches_rust_api_bitwise() {
    let signal = quiet_signal(48_000);
    let (code, out) = call_zwtv(&signal, FS, 0);
    assert_eq!(code, ISO532_OK);
    let want = iso532::loudness_zwtv(&signal, FS, iso532::FieldType::Free).unwrap();
    assert_eq!(out.n, want.n);
    assert_eq!(out.spec, want.n_specific);
    assert_eq!(out.bark, want.bark_axis);
    assert_eq!(out.time, want.time_axis);
}

#[test]
fn zwtv_diffuse_field_matches_rust_api() {
    let signal = quiet_signal(9_600);
    let (code, out) = call_zwtv(&signal, FS, 1);
    assert_eq!(code, ISO532_OK);
    let want = iso532::loudness_zwtv(&signal, FS, iso532::FieldType::Diffuse).unwrap();
    assert_eq!(out.n, want.n);
}

#[test]
fn zwst_happy_path_matches_rust_api_bitwise() {
    let signal = quiet_signal(48_000);
    let mut n = 0.0_f64;
    let mut spec = vec![0.0_f64; 240];
    let mut bark = vec![0.0_f64; 240];
    let code = unsafe {
        iso532_loudness_zwst(
            signal.as_ptr(),
            signal.len(),
            FS,
            0,
            &mut n,
            spec.as_mut_ptr(),
            bark.as_mut_ptr(),
        )
    };
    assert_eq!(code, ISO532_OK);
    let want = iso532::loudness_zwst(&signal, FS, iso532::FieldType::Free).unwrap();
    assert_eq!(n, want.n);
    assert_eq!(spec, want.n_specific);
    assert_eq!(bark, want.bark_axis);
}

#[test]
fn error_mapping_matches_spec_table() {
    // 2: SignalTooShort(< 4800 樣本)
    let (code, _) = call_zwtv(&quiet_signal(100), FS, 0);
    assert_eq!(code, ISO532_ERR_SIGNAL_TOO_SHORT);
    // 3: UnsupportedSampleRate
    let (code, _) = call_zwtv(&quiet_signal(48_000), 44_100.0, 0);
    assert_eq!(code, ISO532_ERR_UNSUPPORTED_SAMPLE_RATE);
    // 1: LevelExceeds120dB
    let (code, _) = call_zwtv(&loud_low_signal(), FS, 0);
    assert_eq!(code, ISO532_ERR_LEVEL_EXCEEDS_120DB);
    // -3: field_type 非 0/1
    let (code, _) = call_zwtv(&quiet_signal(48_000), FS, 2);
    assert_eq!(code, ISO532_ERR_INVALID_FIELD_TYPE);
}

#[test]
fn null_pointers_return_err_null() {
    let signal = quiet_signal(4_800);
    let frames = iso532_zwtv_out_frames(signal.len());
    let mut n = vec![0.0; frames];
    let mut spec = vec![0.0; 240 * frames];
    let mut bark = vec![0.0; 240];
    let mut time = vec![0.0; frames];
    // signal 為 NULL
    let code = unsafe {
        iso532_loudness_zwtv(
            std::ptr::null(), signal.len(), FS, 0,
            n.as_mut_ptr(), spec.as_mut_ptr(), bark.as_mut_ptr(), time.as_mut_ptr(),
        )
    };
    assert_eq!(code, ISO532_ERR_NULL_POINTER);
    // 每個輸出指標各自為 NULL
    for hole in 0..4 {
        let ptrs: Vec<*mut f64> = vec![n.as_mut_ptr(), spec.as_mut_ptr(), bark.as_mut_ptr(), time.as_mut_ptr()]
            .into_iter()
            .enumerate()
            .map(|(i, p)| if i == hole { std::ptr::null_mut() } else { p })
            .collect();
        let code = unsafe {
            iso532_loudness_zwtv(signal.as_ptr(), signal.len(), FS, 0, ptrs[0], ptrs[1], ptrs[2], ptrs[3])
        };
        assert_eq!(code, ISO532_ERR_NULL_POINTER, "hole={hole}");
    }
    // zwst: signal NULL
    let code = unsafe {
        iso532_loudness_zwst(std::ptr::null(), 48_000, FS, 0, &mut 0.0, spec.as_mut_ptr(), bark.as_mut_ptr())
    };
    assert_eq!(code, ISO532_ERR_NULL_POINTER);
}

/// spec §9:200 組隨機有效長度(4800..=48000),查詢值 == 實際輸出長度。
/// 約 15–90 秒(每輪跑完整 pipeline)。
#[test]
fn out_frames_query_matches_actual_for_random_valid_lengths() {
    let mut state = 0x5321_u64;
    for round in 0..200 {
        state = state
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        let len = 4800 + ((state >> 33) % (48_000 - 4800 + 1)) as usize;
        let want = iso532::loudness_zwtv(&quiet_signal(len), FS, iso532::FieldType::Free)
            .unwrap()
            .n
            .len();
        assert_eq!(iso532_zwtv_out_frames(len), want, "round={round} len={len}");
    }
}

/// 查詢函式對 0..4800(無效長度區)必須不 panic(純函數契約)。
#[test]
fn out_frames_query_never_panics_below_min_length() {
    for len in 0..4800 {
        let _ = iso532_zwtv_out_frames(len);
    }
}

// ---- panic 注入(spec §9;cargo test --features test-panic)----

#[cfg(feature = "test-panic")]
#[test]
fn injected_panic_returns_err_panic_not_abort() {
    assert_eq!(iso532__test_panic(), ISO532_ERR_PANIC);
}

/// rayon 工作項 panic 會在 join 點 resume——證實被 guarded() 接住(不假設)。
#[cfg(feature = "test-panic")]
#[test]
fn rayon_worker_panic_is_caught_at_ffi_boundary() {
    assert_eq!(iso532__test_panic_rayon(), ISO532_ERR_PANIC);
}

// ---- R3-P3 跨語言 bitwise 契約的凍結工具(手動執行)----

/// 與 iso532-py/tests/test_smoke.py 的訊號完全一致:純整數演算,
/// 無 libm,Python/Rust 逐位相同(sin 合成會因 libm ULP 差異炸 hash)。
fn py_contract_signal() -> Vec<f64> {
    (0..48_000_u64)
        .map(|i| ((i * 2_654_435_761) % 96_001) as f64 / 96_000.0 * 0.02 - 0.01)
        .collect()
}

fn fnv1a_f64(values: &[f64]) -> u64 {
    // 複製自 iso532/tests/common/mod.rs(跨 crate 無法共用測試模組)
    let mut hash = 0xcbf2_9ce4_8422_2325_u64;
    for value in values {
        for byte in value.to_le_bytes() {
            hash ^= u64::from(byte);
            hash = hash.wrapping_mul(0x0000_0100_0000_01b3);
        }
    }
    hash
}

#[test]
#[ignore = "manual: freeze constants for iso532-py/tests/test_smoke.py (R3-P3)"]
fn dump_py_bitwise_contract_hashes() {
    let r = iso532::loudness_zwtv(&py_contract_signal(), FS, iso532::FieldType::Free).unwrap();
    eprintln!(
        "py-contract: n={:#018x} time={:#018x} frames={}",
        fnv1a_f64(&r.n),
        fnv1a_f64(&r.time_axis),
        r.n.len()
    );
}
```

- [ ] **Step 4: 確認 red(編譯失敗,函式尚不存在)**

```bash
cd iso532-ffi && cargo test 2>&1 | head -20
```

Expected: FAIL,`cannot find function iso532_zwtv_out_frames`(等)。

- [ ] **Step 5: Commit**

```bash
cd /d/ISO532
git add iso532-ffi/Cargo.toml iso532-ffi/src/lib.rs iso532-ffi/tests/ffi.rs
git commit -m "test: add failing FFI contract tests for iso532-ffi (R3-P2)"
```

---

### Task 2: 實作 extern "C" 層(green)

**Files:**
- Modify: `iso532-ffi/src/lib.rs`(常數之後追加)

- [ ] **Step 1: 追加實作(完整程式碼)**

```rust
use std::panic::{catch_unwind, AssertUnwindSafe};

use iso532::{loudness_zwst, loudness_zwtv, FieldType, Iso532Error};

fn error_code(e: &Iso532Error) -> i32 {
    match e {
        Iso532Error::LevelExceeds120dB => ISO532_ERR_LEVEL_EXCEEDS_120DB,
        Iso532Error::SignalTooShort { .. } => ISO532_ERR_SIGNAL_TOO_SHORT,
        Iso532Error::UnsupportedSampleRate(_) => ISO532_ERR_UNSUPPORTED_SAMPLE_RATE,
    }
}

fn field_from(v: i32) -> Option<FieldType> {
    match v {
        0 => Some(FieldType::Free),
        1 => Some(FieldType::Diffuse),
        _ => None,
    }
}

/// 統一 panic 邊界:所有 extern fn 的函式體都必須整體通過這裡。
fn guarded(f: impl FnOnce() -> i32) -> i32 {
    catch_unwind(AssertUnwindSafe(f)).unwrap_or(ISO532_ERR_PANIC)
}

/// Number of output frames `iso532_loudness_zwtv` will write for a signal of
/// `signal_len` samples: ceil(ceil(signal_len/24)/4). Pure; does not validate
/// (validation happens in the main call).
#[no_mangle]
pub extern "C" fn iso532_zwtv_out_frames(signal_len: usize) -> usize {
    signal_len.div_ceil(24).div_ceil(4)
}

/// Time-varying (zwtv) loudness. Caller allocates every buffer:
/// out_n[frames], out_n_specific[240*frames] (bark-major, row-major),
/// out_bark[240], out_time[frames]; frames = iso532_zwtv_out_frames(signal_len).
/// Returns 0 on success (see error-code defines). Uses a process-wide thread
/// pool (rayon).
///
/// # Safety
/// `signal` must be valid for `signal_len` reads; each out pointer must be
/// valid for the writes documented above.
#[no_mangle]
pub unsafe extern "C" fn iso532_loudness_zwtv(
    signal: *const f64,
    signal_len: usize,
    fs: f64,
    field_type: i32,
    out_n: *mut f64,
    out_n_specific: *mut f64,
    out_bark: *mut f64,
    out_time: *mut f64,
) -> i32 {
    guarded(|| {
        if signal.is_null()
            || out_n.is_null()
            || out_n_specific.is_null()
            || out_bark.is_null()
            || out_time.is_null()
        {
            return ISO532_ERR_NULL_POINTER;
        }
        let Some(field) = field_from(field_type) else {
            return ISO532_ERR_INVALID_FIELD_TYPE;
        };
        // SAFETY: 呼叫端契約(見函式 Safety 註解);closure 不繼承 unsafe fn
        // 的 unsafe 語境,故此處需明確 unsafe 區塊。
        let signal = unsafe { std::slice::from_raw_parts(signal, signal_len) };
        match loudness_zwtv(signal, fs, field) {
            Ok(r) => {
                let frames = r.n.len();
                debug_assert_eq!(frames, iso532_zwtv_out_frames(signal_len));
                // SAFETY: 呼叫端契約——各緩衝大小如上;來源為剛建構的 Vec。
                unsafe {
                    std::ptr::copy_nonoverlapping(r.n.as_ptr(), out_n, frames);
                    std::ptr::copy_nonoverlapping(r.n_specific.as_ptr(), out_n_specific, 240 * frames);
                    std::ptr::copy_nonoverlapping(r.bark_axis.as_ptr(), out_bark, 240);
                    std::ptr::copy_nonoverlapping(r.time_axis.as_ptr(), out_time, frames);
                }
                ISO532_OK
            }
            Err(e) => error_code(&e),
        }
    })
}

/// Stationary (zwst) loudness. Caller allocates: out_n[1],
/// out_n_specific[240], out_bark[240]. Returns 0 on success.
///
/// # Safety
/// `signal` must be valid for `signal_len` reads; each out pointer must be
/// valid for the writes documented above.
#[no_mangle]
pub unsafe extern "C" fn iso532_loudness_zwst(
    signal: *const f64,
    signal_len: usize,
    fs: f64,
    field_type: i32,
    out_n: *mut f64,
    out_n_specific: *mut f64,
    out_bark: *mut f64,
) -> i32 {
    guarded(|| {
        if signal.is_null() || out_n.is_null() || out_n_specific.is_null() || out_bark.is_null() {
            return ISO532_ERR_NULL_POINTER;
        }
        let Some(field) = field_from(field_type) else {
            return ISO532_ERR_INVALID_FIELD_TYPE;
        };
        // SAFETY: 呼叫端契約(見函式 Safety 註解)。
        let signal = unsafe { std::slice::from_raw_parts(signal, signal_len) };
        match loudness_zwst(signal, fs, field) {
            Ok(r) => {
                // SAFETY: 呼叫端契約——out_n 1 個、spec/bark 各 240 個 f64。
                unsafe {
                    *out_n = r.n;
                    std::ptr::copy_nonoverlapping(r.n_specific.as_ptr(), out_n_specific, 240);
                    std::ptr::copy_nonoverlapping(r.bark_axis.as_ptr(), out_bark, 240);
                }
                ISO532_OK
            }
            Err(e) => error_code(&e),
        }
    })
}

// ---- panic 注入(僅 test-panic feature;不進 header)----

/// 驗證 guarded() 邊界。僅測試用;release 交付不含此符號。
#[cfg(feature = "test-panic")]
#[no_mangle]
pub extern "C" fn iso532__test_panic() -> i32 {
    guarded(|| panic!("test-panic: direct"))
}

/// rayon 工作項 panic 在 join 點 resume——本函式證實它被 guarded() 接住。
#[cfg(feature = "test-panic")]
#[no_mangle]
pub extern "C" fn iso532__test_panic_rayon() -> i32 {
    guarded(|| {
        use rayon::prelude::*;
        (0..64_i32).into_par_iter().for_each(|i| {
            if i == 33 {
                panic!("test-panic: inside rayon worker");
            }
        });
        ISO532_OK
    })
}
```

- [ ] **Step 2: 一般測試 green(panic 測試 stderr 會有 panic 訊息,屬預期)**

```bash
cd iso532-ffi && cargo test
```

Expected: 全 PASS(property test 可能跑 15–90 秒);`dump_py_bitwise_contract_hashes` 顯示 ignored。

- [ ] **Step 3: panic 注入測試 green**

```bash
cargo test --features test-panic
```

Expected: 全 PASS,含 `injected_panic_returns_err_panic_not_abort` 與 `rayon_worker_panic_is_caught_at_ffi_boundary`。

- [ ] **Step 4: fmt + clippy 乾淨**

```bash
cargo fmt && cargo clippy --all-targets --all-features -- -D warnings
```

Expected: 無警告。

- [ ] **Step 5: Commit**

```bash
cd /d/ISO532
git add iso532-ffi/src/lib.rs
git commit -m "feat: implement iso532-ffi C ABI v0 with panic guard (R3-P2)"
```

---

### Task 3: cbindgen header(commit 入 git)

**Files:**
- Create: `iso532-ffi/cbindgen.toml`
- Create: `iso532-ffi/include/iso532.h`(生成後 commit)

- [ ] **Step 1: cbindgen.toml**

```toml
language = "C"
cpp_compat = true
include_guard = "ISO532_H"
usize_is_size_t = true
header = """/* iso532 C ABI — v0, pre-1.0: may change until R5 freezes v1 (risk R-17).
 * Generated by cbindgen from iso532-ffi; do not edit by hand.
 * Regenerate: cbindgen --config cbindgen.toml --crate iso532-ffi --output include/iso532.h */"""

[export]
exclude = ["iso532__test_panic", "iso532__test_panic_rayon"]
```

- [ ] **Step 2: 安裝 cbindgen 並生成**

```bash
cargo install cbindgen --locked
cd /d/ISO532/iso532-ffi
cbindgen --config cbindgen.toml --crate iso532-ffi --output include/iso532.h
```

- [ ] **Step 3: 檢查 header 內容**

```bash
grep -E "iso532_(zwtv_out_frames|loudness_zwtv|loudness_zwst)" include/iso532.h
grep -c "ISO532_" include/iso532.h
grep -c "test_panic" include/iso532.h
```

Expected: 三個函式宣告都在(型別 `size_t`/`int32_t`/`double*`);錯誤碼常數(`ISO532_OK` 等 7 個)以 `#define` 出現;`test_panic` 出現 0 次。**若常數沒被生成:在 lib.rs 各常數上加 `/// cbindgen:ignore` 的反向處理不適用——改查 cbindgen 版本 ≥0.26 並回報;C smoke 與 Rust 測試都不依賴 #define(用字面值),不阻塞。**

- [ ] **Step 4: Commit**

```bash
cd /d/ISO532
git add iso532-ffi/cbindgen.toml iso532-ffi/include/iso532.h
git commit -m "feat: commit cbindgen-generated iso532.h (C ABI v0, R-17 marked)"
```

---

### Task 4: C smoke test + CI ffi job

**Files:**
- Create: `iso532-ffi/tests/smoke.c`
- Modify: `.github/workflows/ci.yml`(jobs: 下追加 ffi job)

- [ ] **Step 1: smoke.c(完整程式碼;固定 48000 樣本 → frames 必為 500)**

```c
/* C smoke test for the committed include/iso532.h (spec §9).
 * Compiled by CI with gcc (ubuntu) and MSVC cl (windows) against the
 * cdylib; any signature drift in the committed header fails compilation. */
#include <math.h>
#include <stdint.h>
#include <stdio.h>

#include "iso532.h"

#define LEN 48000
#define FRAMES 500 /* ceil(ceil(48000/24)/4) */

static double signal[LEN];
static double out_n[FRAMES];
static double out_spec[240 * FRAMES];
static double out_bark[240];
static double out_time[FRAMES];

int main(void) {
    size_t frames;
    int32_t code;
    size_t i;

    for (i = 0; i < LEN; i++) {
        /* 與 Rust 測試同款整數演算訊號,~54 dB SPL,無錯誤路徑 */
        signal[i] = (double)(i % 480) / 480.0 * 0.02 - 0.01;
    }

    frames = iso532_zwtv_out_frames(LEN);
    if (frames != FRAMES) {
        fprintf(stderr, "frames: got %zu want %d\n", frames, FRAMES);
        return 1;
    }

    code = iso532_loudness_zwtv(signal, LEN, 48000.0, 0, out_n, out_spec,
                                out_bark, out_time);
    if (code != 0) {
        fprintf(stderr, "zwtv: code %d\n", (int)code);
        return 1;
    }
    for (i = 0; i < FRAMES; i++) {
        if (!isfinite(out_n[i]) || out_n[i] < 0.0) {
            fprintf(stderr, "zwtv: out_n[%zu] = %f\n", i, out_n[i]);
            return 1;
        }
    }
    if (out_bark[0] < 0.09 || out_bark[0] > 0.11 || out_bark[239] < 23.9 ||
        out_bark[239] > 24.1) {
        fprintf(stderr, "bark axis: [%f, %f]\n", out_bark[0], out_bark[239]);
        return 1;
    }

    code = iso532_loudness_zwst(signal, LEN, 48000.0, 0, out_n, out_spec,
                                out_bark);
    if (code != 0) {
        fprintf(stderr, "zwst: code %d\n", (int)code);
        return 1;
    }
    if (!isfinite(out_n[0]) || out_n[0] <= 0.0) {
        fprintf(stderr, "zwst: n = %f\n", out_n[0]);
        return 1;
    }

    /* 錯誤碼 smoke:fs 不支援 → 3(字面值,不依賴 #define) */
    code = iso532_loudness_zwtv(signal, LEN, 44100.0, 0, out_n, out_spec,
                                out_bark, out_time);
    if (code != 3) {
        fprintf(stderr, "error mapping: got %d want 3\n", (int)code);
        return 1;
    }

    printf("smoke ok: frames=%zu zwtv_n0=%f\n", frames, out_n[0]);
    return 0;
}
```

- [ ] **Step 2: 本機驗證(Windows/MSVC——需要 VS Build Tools;若本機無 cl,跳過本步,CI 驗)**

```bash
cd /d/ISO532/iso532-ffi && cargo build --release
# 於「x64 Native Tools Command Prompt」或已載入 vcvars 的 shell:
#   cl /nologo /Iinclude tests\smoke.c /link /LIBPATH:target\release iso532_ffi.dll.lib
#   copy target\release\iso532_ffi.dll . && smoke.exe
```

Expected: `smoke ok: frames=500 zwtv_n0=...`。

- [ ] **Step 3: ci.yml 追加 ffi job(`jobs:` 層級,與現有 `test` 平行)**

```yaml
  ffi:
    strategy:
      fail-fast: false
      matrix:
        os: [windows-latest, ubuntu-latest]
    runs-on: ${{ matrix.os }}
    defaults:
      run:
        working-directory: iso532-ffi
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with:
          components: rustfmt, clippy
      - uses: Swatinem/rust-cache@v2
        with:
          workspaces: iso532-ffi
      - run: cargo fmt --check
      - run: cargo clippy --all-targets --all-features -- -D warnings
      # 一般測試 + panic 注入(test-panic feature 打開時兩者都跑)
      - run: cargo test --features test-panic
      - run: cargo build --release
      - name: C smoke (gcc)
        if: matrix.os == 'ubuntu-latest'
        run: |
          gcc -Wall -Wextra -Iinclude tests/smoke.c -Ltarget/release -liso532_ffi -lm -o smoke
          LD_LIBRARY_PATH=target/release ./smoke
      - uses: ilammy/msvc-dev-cmd@v1
        if: matrix.os == 'windows-latest'
      - name: C smoke (MSVC)
        if: matrix.os == 'windows-latest'
        shell: cmd
        run: |
          cl /nologo /W3 /Iinclude tests\smoke.c /link /LIBPATH:target\release iso532_ffi.dll.lib
          copy target\release\iso532_ffi.dll . >NUL
          smoke.exe
```

- [ ] **Step 4: Commit + push**

```bash
cd /d/ISO532
git add iso532-ffi/tests/smoke.c .github/workflows/ci.yml
git commit -m "ci: add ffi job with dual-platform C smoke test (R3-P2)"
git push
```

- [ ] **Step 5: 請使用者確認 GitHub Actions**

無 gh CLI/token——請使用者開 Actions 頁確認 `ffi` job 雙平台全綠(`test` job 也須維持全綠)。紅燈時抄回失敗 log 再迭代。

---

### Task 5: Exit Gate 檢查 + 收尾

- [ ] **Step 1: 主 crate 零 diff 確認**

```bash
cd /d/ISO532 && git diff --stat HEAD -- iso532/src/ && git log --oneline -5 -- iso532/src/
```

Expected: 本 phase 期間 `iso532/src/` 無任何變更。

- [ ] **Step 2: 在本檔尾追加收尾註記並 commit**

```markdown
---
## 收尾註記(執行完成後填)
- CI run:<綠燈 run 連結或 commit>;ffi job 雙平台全綠。
- 本機:cargo test / --features test-panic / fmt / clippy 全過。
- property test 實測耗時:<秒>。
- 偏差(若有):<無/列點>
```

```bash
git add docs/superpowers/plans/phases/phase-r3-2-ffi.md
git commit -m "docs: R3-P2 closeout — C ABI v0 landed" && git push
```

---
## 收尾註記(2026-07-10)
- CI run:尚未執行;本階段依任務指示未 push。`ffi` job 的 Windows/Ubuntu 結果待主代理審查並 push 後確認,不得視為已綠。
- 本機:`cargo test`、`cargo test --features test-panic`、`cargo fmt --check`、`cargo clippy --all-targets --all-features -- -D warnings` 全過;panic 注入含 direct 與 Rayon worker 兩路。
- property test:200 組確實跑完;單測 body 7.89 秒,wall 8.130 秒。
- R3-P3 bitwise freeze:`n=0x44e6822074554786`,`time=0xf076bcb342595537`,`frames=500`。
- header:cbindgen 0.29.4 重生成零 diff;3 個 ABI 函式、7 個錯誤碼常數、0 個 `test_panic`。
- C smoke:本機 VS 2022 Community x64 MSVC 真實編譯、連結與執行成功:`smoke ok: frames=500 zwtv_n0=3.779000`。編譯因 cp950 無法表示 UTF-8 註解而有 C4819 warning,不影響 ABI 或執行;CI 的 gcc/MSVC 尚待執行。
- `iso532/src/`:相對本階段起點 `3c4086b` 零 diff。
- 偏差:plan 未列 `iso532-ffi/Cargo.lock`,但此 crate 交付 cdylib/staticlib,為可重現交付而納入版本控制;Task 1 測試經 `cargo fmt` 的機械排版一併收入 Task 2 commit。
