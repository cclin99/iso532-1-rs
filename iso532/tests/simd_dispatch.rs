use iso532::simd::{avx2_available, set_force_scalar, use_avx2};

#[test]
fn force_scalar_overrides_runtime_detection() {
    let _ = avx2_available();

    set_force_scalar(true);
    assert!(!use_avx2());

    set_force_scalar(false);
    assert_eq!(use_avx2(), avx2_available());
}
