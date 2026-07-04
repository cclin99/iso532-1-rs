use std::sync::atomic::{AtomicBool, Ordering};

static FORCE_SCALAR: AtomicBool = AtomicBool::new(false);

#[inline]
pub fn avx2_available() -> bool {
    #[cfg(target_arch = "x86_64")]
    {
        std::arch::is_x86_feature_detected!("avx2") && std::arch::is_x86_feature_detected!("fma")
    }
    #[cfg(not(target_arch = "x86_64"))]
    {
        false
    }
}

pub fn set_force_scalar(value: bool) {
    FORCE_SCALAR.store(value, Ordering::Relaxed);
}

#[inline]
pub fn use_avx2() -> bool {
    avx2_available() && !FORCE_SCALAR.load(Ordering::Relaxed)
}
