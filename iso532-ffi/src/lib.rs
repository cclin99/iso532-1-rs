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
                    std::ptr::copy_nonoverlapping(
                        r.n_specific.as_ptr(),
                        out_n_specific,
                        240 * frames,
                    );
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
