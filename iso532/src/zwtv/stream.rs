use crate::core::calc_slopes::calc_slopes_n_only;
use crate::core::main_loudness::main_loudness_clamped;
use crate::sone2phon::sone2phon;
use crate::zwtv::nonlinear_decay::{nl_coeffs, NlBandState};
use crate::zwtv::temporal_weighting::TwState;
use crate::zwtv::third_octave_levels::{intensity_to_db, TolBandState, DEC_FACTOR};
use crate::zwtv::OUT_DECIM;
use crate::FieldType;

/// Conservative convergence window: ceil((8*75 ms + 8*70 ms) / 2 ms).
///
/// The original 5-tau-per-stage estimate did not satisfy the 1e-9 contract:
/// the synthetic gate first remains below 1e-9 at frame 544.
pub const N_WARMUP_FRAMES: u64 = 580;

#[repr(transparent)]
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct FrameFlags(u32);

impl FrameFlags {
    pub const CLAMPED_120DB: Self = Self(1);
    pub const NONFINITE_INPUT: Self = Self(1 << 1);
    pub const WARMUP: Self = Self(1 << 2);

    pub const fn bits(self) -> u32 {
        self.0
    }
    pub const fn contains(self, other: Self) -> bool {
        self.0 & other.0 == other.0
    }
    pub fn insert(&mut self, other: Self) {
        self.0 |= other.0;
    }
    pub fn take(&mut self) -> Self {
        std::mem::replace(self, Self(0))
    }
}

#[repr(C)]
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub struct StreamFrame {
    pub t_frame_index: u64,
    pub n: f64,
    pub n_phon: f64,
    pub flags: FrameFlags,
    pub _reserved: u32,
}

#[cfg(target_arch = "x86_64")]
struct DenormalGuard {
    saved: u32,
}

#[cfg(target_arch = "x86_64")]
impl DenormalGuard {
    fn new() -> Self {
        #[allow(deprecated)]
        let saved = unsafe { std::arch::x86_64::_mm_getcsr() };
        #[allow(deprecated)]
        unsafe {
            std::arch::x86_64::_mm_setcsr(saved | 0x8040)
        };
        Self { saved }
    }
}

#[cfg(target_arch = "x86_64")]
impl Drop for DenormalGuard {
    fn drop(&mut self) {
        #[allow(deprecated)]
        unsafe {
            std::arch::x86_64::_mm_setcsr(self.saved)
        };
    }
}

#[cfg(not(target_arch = "x86_64"))]
struct DenormalGuard;
#[cfg(not(target_arch = "x86_64"))]
impl DenormalGuard {
    fn new() -> Self {
        // TODO(R7): use the aarch64 FPCR FZ bit.
        Self
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
        groups: Box<[super::nonlinear_decay::NlGroupState; 5]>,
        consts: super::nonlinear_decay::NlConsts,
        tail: NlBandState,
    },
}

fn new_tol_stage() -> TolStage {
    #[cfg(target_arch = "x86_64")]
    if crate::simd::use_avx2() {
        return TolStage::Avx2(Box::new(std::array::from_fn(|group| unsafe {
            super::third_octave_levels::TolGroupState::new(group)
        })));
    }
    TolStage::Scalar(Box::new(std::array::from_fn(TolBandState::new)))
}

fn new_nl_stage(b: [f64; 6]) -> NlStage {
    #[cfg(target_arch = "x86_64")]
    if crate::simd::use_avx2() {
        return unsafe {
            NlStage::Avx2 {
                groups: Box::new(std::array::from_fn(|_| {
                    super::nonlinear_decay::NlGroupState::zero()
                })),
                consts: super::nonlinear_decay::NlConsts::new(b),
                tail: NlBandState::default(),
            }
        };
    }
    NlStage::Scalar([NlBandState::default(); 21])
}

fn advance_nl_stage(
    stage: &mut NlStage,
    b: &[f64; 6],
    held: &[f64; 21],
    next: &[f64; 21],
) -> [f64; 21] {
    let mut out = [0.0; 21];
    match stage {
        NlStage::Scalar(states) => {
            for band in 0..21 {
                out[band] = states[band].advance_frame(held[band], next[band], b);
            }
        }
        #[cfg(target_arch = "x86_64")]
        NlStage::Avx2 {
            groups,
            consts,
            tail,
        } => {
            use std::arch::x86_64::{_mm256_loadu_pd, _mm256_storeu_pd};
            for (group, state) in groups.iter_mut().enumerate() {
                let band = group * 4;
                unsafe {
                    let row = _mm256_loadu_pd(held[band..].as_ptr());
                    let next_row = _mm256_loadu_pd(next[band..].as_ptr());
                    let value = state.advance_frame(row, next_row, consts);
                    _mm256_storeu_pd(out[band..].as_mut_ptr(), value);
                }
            }
            out[20] = tail.advance_frame(held[20], next[20], b);
        }
    }
    out
}

/// Stateful 48 kHz ISO 532-1 time-varying loudness processor.
///
/// Push and flush allocate no memory and never enter Rayon. Output latency is
/// one 24-sample internal frame.
pub struct ZwtvStream {
    field: FieldType,
    tol: TolStage,
    nl_b: [f64; 6],
    nl: NlStage,
    tw: TwState,
    held_core: [f64; 21],
    has_held: bool,
    sample_phase: usize,
    t_internal: u64,
    emitted_internal: u64,
    pending: FrameFlags,
    flushed: bool,
}

impl ZwtvStream {
    pub fn new(field: FieldType) -> Self {
        let _guard = DenormalGuard::new();
        let nl_b = nl_coeffs();
        Self {
            field,
            tol: new_tol_stage(),
            nl_b,
            nl: new_nl_stage(nl_b),
            tw: TwState::new(),
            held_core: [0.0; 21],
            has_held: false,
            sample_phase: 0,
            t_internal: 0,
            emitted_internal: 0,
            pending: FrameFlags::default(),
            flushed: false,
        }
    }

    pub fn reset(&mut self) {
        *self = Self::new(self.field);
    }
    pub const fn latency_samples() -> usize {
        DEC_FACTOR
    }
    pub const fn max_frames_for_chunk(chunk_len: usize) -> usize {
        chunk_len / (DEC_FACTOR * OUT_DECIM) + 2
    }

    pub fn push(&mut self, chunk: &[f64], out: &mut [StreamFrame]) -> usize {
        assert!(!self.flushed, "push after flush requires reset");
        assert!(out.len() >= Self::max_frames_for_chunk(chunk.len()));
        let _guard = DenormalGuard::new();
        let mut written = 0;
        for &raw in chunk {
            let sample = if raw.is_finite() {
                raw
            } else {
                self.pending.insert(FrameFlags::NONFINITE_INPUT);
                0.0
            };
            let emit = self.sample_phase == 0;
            let tol_frame = self.advance_tol(sample, emit);
            self.sample_phase = (self.sample_phase + 1) % DEC_FACTOR;
            if let Some(frame) = tol_frame {
                written += self.on_internal_frame(frame, &mut out[written..]);
            }
        }
        written
    }

    pub fn flush(&mut self, out: &mut [StreamFrame]) -> usize {
        assert!(!out.is_empty());
        let _guard = DenormalGuard::new();
        if self.flushed || !self.has_held {
            self.flushed = true;
            return 0;
        }
        self.flushed = true;
        self.has_held = false;
        let held = self.held_core;
        self.emit_loudness(&held, &[0.0; 21], out)
    }

    fn advance_tol(&mut self, sample: f64, emit: bool) -> Option<[f64; 28]> {
        let mut frame = [0.0; 28];
        match &mut self.tol {
            TolStage::Scalar(states) => {
                for (band, state) in states.iter_mut().enumerate() {
                    let intensity = state.advance(sample);
                    if emit {
                        frame[band] = intensity_to_db(intensity);
                    }
                }
            }
            #[cfg(target_arch = "x86_64")]
            TolStage::Avx2(groups) => {
                use std::arch::x86_64::_mm256_storeu_pd;
                for (group, state) in groups.iter_mut().enumerate() {
                    let intensity = unsafe { state.advance(sample) };
                    if emit {
                        let mut lanes = [0.0; 4];
                        unsafe { _mm256_storeu_pd(lanes.as_mut_ptr(), intensity) };
                        for lane in 0..4 {
                            frame[group * 4 + lane] = intensity_to_db(lanes[lane]);
                        }
                    }
                }
            }
        }
        emit.then_some(frame)
    }

    fn on_internal_frame(&mut self, tol_db: [f64; 28], out: &mut [StreamFrame]) -> usize {
        let (core, clamped) = main_loudness_clamped(&tol_db, self.field);
        if clamped {
            self.pending.insert(FrameFlags::CLAMPED_120DB);
        }
        let wrote = if self.has_held {
            let held = self.held_core;
            self.emit_loudness(&held, &core, out)
        } else {
            0
        };
        self.held_core = core;
        self.has_held = true;
        self.t_internal += 1;
        wrote
    }

    fn emit_loudness(
        &mut self,
        held: &[f64; 21],
        next: &[f64; 21],
        out: &mut [StreamFrame],
    ) -> usize {
        let nl = advance_nl_stage(&mut self.nl, &self.nl_b, held, next);
        let n = self.tw.advance(calc_slopes_n_only(&nl));
        let internal = self.emitted_internal;
        self.emitted_internal += 1;
        if !internal.is_multiple_of(OUT_DECIM as u64) {
            return 0;
        }
        let index = internal / OUT_DECIM as u64;
        let mut flags = self.pending.take();
        if index < N_WARMUP_FRAMES {
            flags.insert(FrameFlags::WARMUP);
        }
        out[0] = StreamFrame {
            t_frame_index: index,
            n,
            n_phon: sone2phon(n),
            flags,
            _reserved: 0,
        };
        1
    }
}

#[doc(hidden)]
pub fn zwtv_reference_zerostate(signal: &[f64], field: FieldType) -> Vec<f64> {
    let _guard = DenormalGuard::new();
    let (tol, n_time) = super::third_octave_levels::third_octave_levels_with_mode(
        signal,
        super::ParMode::Sequential,
    );
    let mut core = vec![[0.0; 21]; n_time];
    for t in 0..n_time {
        let frame = std::array::from_fn(|band| tol[band * n_time + t]);
        core[t] = main_loudness_clamped(&frame, field).0;
    }
    let b = nl_coeffs();
    let mut nl = new_nl_stage(b);
    let mut tw = TwState::new();
    let mut out = Vec::with_capacity(n_time.div_ceil(OUT_DECIM));
    for t in 0..n_time {
        let next = if t + 1 < n_time {
            core[t + 1]
        } else {
            [0.0; 21]
        };
        let nl_frame = advance_nl_stage(&mut nl, &b, &core[t], &next);
        let n = tw.advance(calc_slopes_n_only(&nl_frame));
        if t % OUT_DECIM == 0 {
            out.push(n);
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::{FrameFlags, StreamFrame};

    #[test]
    fn flag_bits_and_frame_layout_are_frozen() {
        assert_eq!(FrameFlags::CLAMPED_120DB.bits(), 1);
        assert_eq!(FrameFlags::NONFINITE_INPUT.bits(), 2);
        assert_eq!(FrameFlags::WARMUP.bits(), 4);
        assert_eq!(std::mem::size_of::<StreamFrame>(), 32);
    }
}
