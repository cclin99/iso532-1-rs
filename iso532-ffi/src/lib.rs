//! C ABI v1 for the iso532 crate: batch and stateful streaming APIs.
//!
//! Every extern fn that can panic is wrapped in `catch_unwind` (panic -> -2);
//! this crate must never be built with `panic = "abort"`.

pub const ISO532_OK: i32 = 0;
pub const ISO532_ERR_LEVEL_EXCEEDS_120DB: i32 = 1;
pub const ISO532_ERR_SIGNAL_TOO_SHORT: i32 = 2;
pub const ISO532_ERR_UNSUPPORTED_SAMPLE_RATE: i32 = 3;
pub const ISO532_ERR_NULL_POINTER: i32 = -1;
pub const ISO532_ERR_PANIC: i32 = -2;
pub const ISO532_ERR_INVALID_FIELD_TYPE: i32 = -3;
/// An internal invariant was broken. Stream push/flush also use this code to
/// reject an insufficient out_cap without writing a partial result.
pub const ISO532_ERR_INTERNAL: i32 = -4;
/// field_type 合法值：自由場。
pub const ISO532_FIELD_FREE: i32 = 0;
/// field_type 合法值：擴散場。
pub const ISO532_FIELD_DIFFUSE: i32 = 1;
pub const ISO532_STREAM_FLAG_CLAMPED_120DB: u32 = 1;
pub const ISO532_STREAM_FLAG_NONFINITE_INPUT: u32 = 2;
pub const ISO532_STREAM_FLAG_WARMUP: u32 = 4;
use std::panic::{catch_unwind, AssertUnwindSafe};

use iso532::{loudness_zwst, loudness_zwtv, FieldType};

/// 統一 panic 邊界:所有 extern fn 的函式體都必須整體通過這裡。
fn guarded_or<T>(default: T, f: impl FnOnce() -> T) -> T {
    catch_unwind(AssertUnwindSafe(f)).unwrap_or(default)
}

fn guarded(f: impl FnOnce() -> i32) -> i32 {
    guarded_or(ISO532_ERR_PANIC, f)
}

#[repr(C)]
#[derive(Clone, Copy, Debug, Default)]
/// One 2 ms stream output frame.
///
/// `flags` uses bit 1 for CLAMPED_120DB, bit 2 for NONFINITE_INPUT, and bit 4
/// for WARMUP. WARMUP is set while `t_frame_index < 580`.
pub struct Iso532StreamFrame {
    pub t_frame_index: u64,
    pub n: f64,
    pub n_phon: f64,
    pub flags: u32,
    pub _reserved: u32,
}

/// Opaque stream handle allocated by iso532_stream_new and released by
/// iso532_stream_free. A handle has no internal lock and must not be called
/// concurrently from multiple threads.
pub struct Iso532Stream {
    inner: iso532::ZwtvStream,
}

const _: () = {
    assert!(std::mem::size_of::<Iso532StreamFrame>() == std::mem::size_of::<iso532::StreamFrame>());
    assert!(
        std::mem::align_of::<Iso532StreamFrame>() == std::mem::align_of::<iso532::StreamFrame>()
    );
    assert!(
        std::mem::offset_of!(Iso532StreamFrame, t_frame_index)
            == std::mem::offset_of!(iso532::StreamFrame, t_frame_index)
    );
    assert!(
        std::mem::offset_of!(Iso532StreamFrame, n) == std::mem::offset_of!(iso532::StreamFrame, n)
    );
    assert!(
        std::mem::offset_of!(Iso532StreamFrame, n_phon)
            == std::mem::offset_of!(iso532::StreamFrame, n_phon)
    );
    assert!(
        std::mem::offset_of!(Iso532StreamFrame, flags)
            == std::mem::offset_of!(iso532::StreamFrame, flags)
    );
    assert!(
        std::mem::offset_of!(Iso532StreamFrame, _reserved)
            == std::mem::offset_of!(iso532::StreamFrame, _reserved)
    );
    assert!(ISO532_STREAM_FLAG_CLAMPED_120DB == iso532::FrameFlags::CLAMPED_120DB.bits());
    assert!(ISO532_STREAM_FLAG_NONFINITE_INPUT == iso532::FrameFlags::NONFINITE_INPUT.bits());
    assert!(ISO532_STREAM_FLAG_WARMUP == iso532::FrameFlags::WARMUP.bits());
};

#[no_mangle]
/// Allocate a baked-in 48 kHz stream with 24 samples (one internal frame) of
/// latency. An invalid field_type returns NULL.
pub extern "C" fn iso532_stream_new(field_type: i32) -> *mut Iso532Stream {
    let Ok(field) = FieldType::try_from(field_type) else {
        return std::ptr::null_mut();
    };
    guarded_or(std::ptr::null_mut(), || {
        Box::into_raw(Box::new(Iso532Stream {
            inner: iso532::ZwtvStream::new(field),
        }))
    })
}

#[no_mangle]
pub extern "C" fn iso532_stream_max_frames(chunk_len: usize) -> usize {
    iso532::ZwtvStream::max_frames_for_chunk(chunk_len)
}

/// Return pending flags observed after the most recent output frame. Before
/// flush the value is provisional and will be attached to the next output
/// frame. Only after flush does it represent undelivered tail events. A null
/// handle returns zero. After a prior push or flush returned -2, the value is
/// undefined and only iso532_stream_free may be called.
///
/// # Safety
/// A non-null handle must be live and must not be accessed concurrently.
#[no_mangle]
pub unsafe extern "C" fn iso532_stream_residual_flags(handle: *const Iso532Stream) -> u32 {
    guarded_or(0, || {
        if handle.is_null() {
            return 0;
        }
        unsafe { (*handle).inner.residual_flags().bits() }
    })
}

/// Push a 48 kHz signal chunk into a stream handle.
///
/// `out` must hold at least `iso532_stream_max_frames(chunk_len)` frames. An
/// insufficient out_cap returns -4, sets `*out_written` to zero, and writes no
/// partial result. A panic returns -2 and poisons the handle; only
/// iso532_stream_free may be called afterward. A push after flush also returns
/// -2 through the internal assertion and has the same poisoned-handle rule.
///
/// # Safety
/// The handle must be live, chunk must contain chunk_len readable doubles,
/// out must contain out_cap writable frames, and out_written must be writable.
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
        unsafe { *out_written = 0 };
        if handle.is_null() || (chunk.is_null() && chunk_len > 0) || out.is_null() {
            return ISO532_ERR_NULL_POINTER;
        }
        if out_cap < iso532_stream_max_frames(chunk_len) {
            return ISO532_ERR_INTERNAL;
        }
        let chunk = if chunk_len == 0 {
            &[]
        } else {
            unsafe { std::slice::from_raw_parts(chunk, chunk_len) }
        };
        let stream = unsafe { &mut (*handle).inner };
        let out =
            unsafe { std::slice::from_raw_parts_mut(out.cast::<iso532::StreamFrame>(), out_cap) };
        let written = stream.push(chunk, out);
        unsafe { *out_written = written };
        ISO532_OK
    })
}

/// Flush the final lookahead frame. out_cap must be at least one. *out_written
/// is zero or one: one frame is written only when the final internal frame is
/// on the 2 ms output grid; zero is not an error. After flush, only
/// iso532_stream_residual_flags and iso532_stream_free may be called.
///
/// # Safety
/// The handle must be live, out must contain at least one writable frame,
/// and out_written must be writable.
#[no_mangle]
pub unsafe extern "C" fn iso532_stream_flush(
    handle: *mut Iso532Stream,
    out: *mut Iso532StreamFrame,
    out_cap: usize,
    out_written: *mut usize,
) -> i32 {
    guarded(|| {
        if out_written.is_null() {
            return ISO532_ERR_NULL_POINTER;
        }
        unsafe { *out_written = 0 };
        if handle.is_null() || out.is_null() {
            return ISO532_ERR_NULL_POINTER;
        }
        if out_cap < 1 {
            return ISO532_ERR_INTERNAL;
        }
        let stream = unsafe { &mut (*handle).inner };
        let out =
            unsafe { std::slice::from_raw_parts_mut(out.cast::<iso532::StreamFrame>(), out_cap) };
        let written = stream.flush(out);
        unsafe { *out_written = written };
        ISO532_OK
    })
}

/// Free a stream handle. A null handle is accepted.
///
/// # Safety
/// A non-null handle must have been returned by iso532_stream_new and not
/// previously freed.
#[no_mangle]
pub unsafe extern "C" fn iso532_stream_free(handle: *mut Iso532Stream) {
    if handle.is_null() {
        return;
    }
    guarded_or((), || unsafe {
        drop(Box::from_raw(handle));
    });
}

/// Number of output frames `iso532_loudness_zwtv` will write for a signal of
/// `signal_len` samples, on the ISO 2 ms output grid. Pure; does not validate
/// (validation happens in the main call). Forwards `iso532::zwtv_out_frames`.
#[no_mangle]
pub extern "C" fn iso532_zwtv_out_frames(signal_len: usize) -> usize {
    iso532::zwtv_out_frames(signal_len)
}

/// Time-varying (zwtv) loudness. Caller allocates every buffer:
/// out_n[frames], out_n_specific[240*frames] (bark-major, row-major),
/// out_bark[240], out_time[frames]; frames = iso532_zwtv_out_frames(signal_len).
/// Returns 0 on success (see error-code defines). Uses a process-wide thread
/// pool (rayon).
///
/// # Safety
/// `signal` must be non-null, 8-byte aligned (a valid `double*`), and valid
/// for `signal_len` reads; each out pointer must be valid (and 8-byte
/// aligned) for the writes documented above. `field_type` must be
/// ISO532_FIELD_FREE (0) or ISO532_FIELD_DIFFUSE (1); other values return
/// ISO532_ERR_INVALID_FIELD_TYPE.
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
        let Ok(field) = FieldType::try_from(field_type) else {
            return ISO532_ERR_INVALID_FIELD_TYPE;
        };
        // SAFETY: 呼叫端契約(見函式 Safety 註解);closure 不繼承 unsafe fn
        // 的 unsafe 語境,故此處需明確 unsafe 區塊。
        let signal = unsafe { std::slice::from_raw_parts(signal, signal_len) };
        match loudness_zwtv(signal, fs, field) {
            Ok(r) => {
                let frames = r.n.len();
                if frames != iso532::zwtv_out_frames(signal_len)
                    || r.n_specific.len() != 240 * frames
                    || r.bark_axis.len() != 240
                    || r.time_axis.len() != frames
                {
                    return ISO532_ERR_INTERNAL;
                }
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
            Err(e) => e.code(),
        }
    })
}

/// Stationary (zwst) loudness. Caller allocates: out_n[1],
/// out_n_specific[240], out_bark[240]. Returns 0 on success.
///
/// # Safety
/// `signal` must be non-null, 8-byte aligned (a valid `double*`), and valid
/// for `signal_len` reads; each out pointer must be valid (and 8-byte
/// aligned) for the writes documented above. `field_type` must be
/// ISO532_FIELD_FREE (0) or ISO532_FIELD_DIFFUSE (1); other values return
/// ISO532_ERR_INVALID_FIELD_TYPE.
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
        let Ok(field) = FieldType::try_from(field_type) else {
            return ISO532_ERR_INVALID_FIELD_TYPE;
        };
        // SAFETY: 呼叫端契約(見函式 Safety 註解)。
        let signal = unsafe { std::slice::from_raw_parts(signal, signal_len) };
        match loudness_zwst(signal, fs, field) {
            Ok(r) => {
                if r.n_specific.len() != 240 || r.bark_axis.len() != 240 {
                    return ISO532_ERR_INTERNAL;
                }
                // SAFETY: 呼叫端契約——out_n 1 個、spec/bark 各 240 個 f64。
                unsafe {
                    *out_n = r.n;
                    std::ptr::copy_nonoverlapping(r.n_specific.as_ptr(), out_n_specific, 240);
                    std::ptr::copy_nonoverlapping(r.bark_axis.as_ptr(), out_bark, 240);
                }
                ISO532_OK
            }
            Err(e) => e.code(),
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

#[cfg(feature = "test-panic")]
#[no_mangle]
pub extern "C" fn iso532__test_panic_stream() -> i32 {
    guarded(|| {
        let _stream = iso532::ZwtvStream::new(FieldType::Free);
        panic!("test-panic: stream path")
    })
}
