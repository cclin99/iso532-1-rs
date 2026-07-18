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
    let (code, out) = call_zwtv(&signal, FS, ISO532_FIELD_FREE);
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
    let (code, _) = call_zwtv(&quiet_signal(100), FS, ISO532_FIELD_FREE);
    assert_eq!(code, ISO532_ERR_SIGNAL_TOO_SHORT);
    // 3: UnsupportedSampleRate
    let (code, _) = call_zwtv(&quiet_signal(48_000), 44_100.0, 0);
    assert_eq!(code, ISO532_ERR_UNSUPPORTED_SAMPLE_RATE);
    // 1: LevelExceeds120dB
    let (code, _) = call_zwtv(&loud_low_signal(), FS, ISO532_FIELD_FREE);
    assert_eq!(code, ISO532_ERR_LEVEL_EXCEEDS_120DB);
    // -3: field_type 非 0/1
    let (code, _) = call_zwtv(&quiet_signal(48_000), FS, 2);
    assert_eq!(code, ISO532_ERR_INVALID_FIELD_TYPE);
}

#[test]
fn field_constants_are_frozen() {
    assert_eq!(ISO532_FIELD_FREE, 0);
    assert_eq!(ISO532_FIELD_DIFFUSE, 1);
    assert_eq!(ISO532_ERR_INTERNAL, -4);
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
            std::ptr::null(),
            signal.len(),
            FS,
            0,
            n.as_mut_ptr(),
            spec.as_mut_ptr(),
            bark.as_mut_ptr(),
            time.as_mut_ptr(),
        )
    };
    assert_eq!(code, ISO532_ERR_NULL_POINTER);
    // 每個輸出指標各自為 NULL
    for hole in 0..4 {
        let ptrs: Vec<*mut f64> = vec![
            n.as_mut_ptr(),
            spec.as_mut_ptr(),
            bark.as_mut_ptr(),
            time.as_mut_ptr(),
        ]
        .into_iter()
        .enumerate()
        .map(|(i, p)| if i == hole { std::ptr::null_mut() } else { p })
        .collect();
        let code = unsafe {
            iso532_loudness_zwtv(
                signal.as_ptr(),
                signal.len(),
                FS,
                0,
                ptrs[0],
                ptrs[1],
                ptrs[2],
                ptrs[3],
            )
        };
        assert_eq!(code, ISO532_ERR_NULL_POINTER, "hole={hole}");
    }
    // zwst: signal NULL
    let code = unsafe {
        iso532_loudness_zwst(
            std::ptr::null(),
            48_000,
            FS,
            0,
            &mut 0.0,
            spec.as_mut_ptr(),
            bark.as_mut_ptr(),
        )
    };
    assert_eq!(code, ISO532_ERR_NULL_POINTER);
}

/// FFI forwarding contract.
#[test]
fn out_frames_query_forwards_core_at_representative_boundaries() {
    for len in [0, 1, 23, 24, 25, 95, 96, 97, 4_799, 4_800, 48_000] {
        assert_eq!(iso532_zwtv_out_frames(len), iso532::zwtv_out_frames(len));
    }
}

/// 查詢函式對 0..4800(無效長度區)必須不 panic(純函數契約)。
#[test]
fn out_frames_query_never_panics_below_min_length() {
    for len in 0..4800 {
        let _ = iso532_zwtv_out_frames(len);
    }
}

#[test]
fn stream_matches_rust_stream_bitwise() {
    let signal = quiet_signal(48_000);
    let mut rust = iso532::ZwtvStream::new(iso532::FieldType::Free);
    let mut rust_out = vec![iso532::StreamFrame::default(); 64];
    let mut rust_frames = Vec::new();
    for chunk in signal.chunks(480) {
        let n = rust.push(chunk, &mut rust_out);
        rust_frames.extend_from_slice(&rust_out[..n]);
    }
    let n = rust.flush(&mut rust_out);
    rust_frames.extend_from_slice(&rust_out[..n]);

    let handle = iso532_stream_new(ISO532_FIELD_FREE);
    assert!(!handle.is_null());
    let mut c_out = vec![Iso532StreamFrame::default(); 64];
    let mut c_frames = Vec::new();
    for chunk in signal.chunks(480) {
        let mut written = 0;
        let code = unsafe {
            iso532_stream_push(
                handle,
                chunk.as_ptr(),
                chunk.len(),
                c_out.as_mut_ptr(),
                c_out.len(),
                &mut written,
            )
        };
        assert_eq!(code, ISO532_OK);
        c_frames.extend_from_slice(&c_out[..written]);
    }
    let mut written = 0;
    assert_eq!(
        unsafe { iso532_stream_flush(handle, c_out.as_mut_ptr(), c_out.len(), &mut written) },
        ISO532_OK
    );
    c_frames.extend_from_slice(&c_out[..written]);
    unsafe { iso532_stream_free(handle) };

    assert_eq!(rust_frames.len(), c_frames.len());
    for (rust, c) in rust_frames.iter().zip(&c_frames) {
        assert_eq!(rust.t_frame_index, c.t_frame_index);
        assert_eq!(rust.n.to_bits(), c.n.to_bits());
        assert_eq!(rust.n_phon.to_bits(), c.n_phon.to_bits());
        assert_eq!(rust.flags.bits(), c.flags);
    }
}

#[test]
fn stream_rejects_small_output_without_consuming_input() {
    let signal = quiet_signal(480);
    let handle = iso532_stream_new(ISO532_FIELD_FREE);
    assert!(!handle.is_null());
    let mut too_small = [Iso532StreamFrame::default(); 1];
    let mut written = usize::MAX;
    assert_eq!(
        unsafe {
            iso532_stream_push(
                handle,
                signal.as_ptr(),
                signal.len(),
                too_small.as_mut_ptr(),
                too_small.len(),
                &mut written,
            )
        },
        ISO532_ERR_INTERNAL
    );
    assert_eq!(written, 0);
    let mut enough = vec![Iso532StreamFrame::default(); iso532_stream_max_frames(signal.len())];
    assert_eq!(
        unsafe {
            iso532_stream_push(
                handle,
                signal.as_ptr(),
                signal.len(),
                enough.as_mut_ptr(),
                enough.len(),
                &mut written,
            )
        },
        ISO532_OK
    );
    assert!(written > 0);
    unsafe { iso532_stream_free(handle) };
}

#[test]
fn stream_max_frames_forwards_rust_contract() {
    for chunk_len in [0, 1, 24, 480, 4096] {
        assert_eq!(
            iso532_stream_max_frames(chunk_len),
            iso532::ZwtvStream::max_frames_for_chunk(chunk_len)
        );
    }
}

#[test]
fn stream_tail_nonfinite_is_exposed_as_residual_flag() {
    let mut signal = vec![0.0; 48_048];
    signal[48_030] = f64::NAN;
    let handle = iso532_stream_new(ISO532_FIELD_FREE);
    assert!(!handle.is_null());
    let mut out = vec![Iso532StreamFrame::default(); iso532_stream_max_frames(signal.len())];
    let mut written = 0;
    assert_eq!(
        unsafe {
            iso532_stream_push(
                handle,
                signal.as_ptr(),
                signal.len(),
                out.as_mut_ptr(),
                out.len(),
                &mut written,
            )
        },
        ISO532_OK
    );
    assert_eq!(
        unsafe { iso532_stream_flush(handle, out.as_mut_ptr(), out.len(), &mut written) },
        ISO532_OK
    );
    assert_eq!(written, 0);
    assert_ne!(
        unsafe { iso532_stream_residual_flags(handle) } & ISO532_STREAM_FLAG_NONFINITE_INPUT,
        0
    );
    unsafe { iso532_stream_free(handle) };
}

#[test]
fn stream_residual_flags_null_handle_returns_zero() {
    assert_eq!(unsafe { iso532_stream_residual_flags(std::ptr::null()) }, 0);
}

#[test]
fn stream_layout_flags_and_null_paths_are_frozen() {
    assert_eq!(
        std::mem::size_of::<Iso532StreamFrame>(),
        std::mem::size_of::<iso532::StreamFrame>()
    );
    assert_eq!(
        std::mem::offset_of!(Iso532StreamFrame, t_frame_index),
        std::mem::offset_of!(iso532::StreamFrame, t_frame_index)
    );
    assert_eq!(
        std::mem::offset_of!(Iso532StreamFrame, n),
        std::mem::offset_of!(iso532::StreamFrame, n)
    );
    assert_eq!(
        std::mem::offset_of!(Iso532StreamFrame, n_phon),
        std::mem::offset_of!(iso532::StreamFrame, n_phon)
    );
    assert_eq!(
        std::mem::offset_of!(Iso532StreamFrame, flags),
        std::mem::offset_of!(iso532::StreamFrame, flags)
    );
    assert_eq!(
        std::mem::offset_of!(Iso532StreamFrame, _reserved),
        std::mem::offset_of!(iso532::StreamFrame, _reserved)
    );
    assert_eq!(ISO532_STREAM_FLAG_CLAMPED_120DB, 1);
    assert_eq!(ISO532_STREAM_FLAG_NONFINITE_INPUT, 2);
    assert_eq!(ISO532_STREAM_FLAG_WARMUP, 4);
    assert!(iso532_stream_new(2).is_null());
    let mut written = 1;
    assert_eq!(
        unsafe {
            iso532_stream_push(
                std::ptr::null_mut(),
                std::ptr::null(),
                0,
                std::ptr::null_mut(),
                0,
                &mut written,
            )
        },
        ISO532_ERR_NULL_POINTER
    );
    assert_eq!(written, 0);
    unsafe { iso532_stream_free(std::ptr::null_mut()) };
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

#[cfg(feature = "test-panic")]
#[test]
fn stream_path_panic_is_caught_at_ffi_boundary() {
    assert_eq!(iso532__test_panic_stream(), ISO532_ERR_PANIC);
}
