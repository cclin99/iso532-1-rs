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
