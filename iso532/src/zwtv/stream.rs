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
    Scalar {
        states: [NlBandState; 21],
        b: [f64; 6],
    },
    #[cfg(target_arch = "x86_64")]
    Avx2 {
        groups: Box<[super::nonlinear_decay::NlGroupState; 5]>,
        consts: super::nonlinear_decay::NlConsts,
        tail: NlBandState,
        b: [f64; 6],
    },
}

fn new_tol_stage(avx2: bool) -> TolStage {
    #[cfg(not(target_arch = "x86_64"))]
    let _ = avx2;
    #[cfg(target_arch = "x86_64")]
    if avx2 {
        return TolStage::Avx2(Box::new(std::array::from_fn(|group| unsafe {
            super::third_octave_levels::TolGroupState::new(group)
        })));
    }
    TolStage::Scalar(Box::new(std::array::from_fn(TolBandState::new)))
}

fn new_nl_stage(b: [f64; 6], avx2: bool) -> NlStage {
    #[cfg(not(target_arch = "x86_64"))]
    let _ = avx2;
    #[cfg(target_arch = "x86_64")]
    if avx2 {
        return unsafe {
            NlStage::Avx2 {
                groups: Box::new(std::array::from_fn(|_| {
                    super::nonlinear_decay::NlGroupState::zero()
                })),
                consts: super::nonlinear_decay::NlConsts::new(b),
                tail: NlBandState::default(),
                b,
            }
        };
    }
    NlStage::Scalar {
        states: [NlBandState::default(); 21],
        b,
    }
}

fn advance_nl_stage(stage: &mut NlStage, held: &[f64; 21], next: &[f64; 21]) -> [f64; 21] {
    let mut out = [0.0; 21];
    match stage {
        NlStage::Scalar { states, b } => {
            for band in 0..21 {
                out[band] = states[band].advance_frame(held[band], next[band], b);
            }
        }
        #[cfg(target_arch = "x86_64")]
        NlStage::Avx2 {
            groups,
            consts,
            tail,
            b,
        } => unsafe { advance_nl_avx2(groups, consts, tail, b, held, next, &mut out) },
    }
    out
}

#[cfg(target_arch = "x86_64")]
#[target_feature(enable = "avx2,fma")]
unsafe fn advance_nl_avx2(
    groups: &mut [super::nonlinear_decay::NlGroupState; 5],
    consts: &super::nonlinear_decay::NlConsts,
    tail: &mut NlBandState,
    b: &[f64; 6],
    held: &[f64; 21],
    next: &[f64; 21],
    out: &mut [f64; 21],
) {
    use std::arch::x86_64::{_mm256_loadu_pd, _mm256_storeu_pd};
    for (group, state) in groups.iter_mut().enumerate() {
        let band = group * 4;
        let row = _mm256_loadu_pd(held[band..].as_ptr());
        let next_row = _mm256_loadu_pd(next[band..].as_ptr());
        let value = state.advance_frame(row, next_row, consts);
        _mm256_storeu_pd(out[band..].as_mut_ptr(), value);
    }
    out[20] = tail.advance_frame(held[20], next[20], b);
}

#[inline(always)]
fn advance_tol_chunk(
    chunk: &[f64],
    sample_phase: &mut usize,
    mut advance: impl FnMut(f64, bool) -> Option<[f64; 28]>,
    mut on_frame: impl FnMut([f64; 28], bool),
) -> bool {
    let mut saw_nonfinite = false;
    for &raw in chunk {
        let sample = if raw.is_finite() {
            raw
        } else {
            saw_nonfinite = true;
            0.0
        };
        let emit = *sample_phase == 0;
        if let Some(frame) = advance(sample, emit) {
            on_frame(frame, saw_nonfinite);
            saw_nonfinite = false;
        }
        *sample_phase = (*sample_phase + 1) % DEC_FACTOR;
    }
    saw_nonfinite
}

fn advance_tol_scalar_chunk(
    states: &mut [TolBandState; 28],
    chunk: &[f64],
    sample_phase: &mut usize,
    on_frame: impl FnMut([f64; 28], bool),
) -> bool {
    advance_tol_chunk(
        chunk,
        sample_phase,
        |sample, emit| {
            if !emit {
                for state in states.iter_mut() {
                    state.advance(sample);
                }
                return None;
            }
            let mut frame = [0.0; 28];
            for (band, state) in states.iter_mut().enumerate() {
                frame[band] = intensity_to_db(state.advance(sample));
            }
            Some(frame)
        },
        on_frame,
    )
}

#[cfg(target_arch = "x86_64")]
#[target_feature(enable = "avx2,fma")]
unsafe fn advance_tol_avx2_chunk(
    groups: &mut [super::third_octave_levels::TolGroupState; 7],
    chunk: &[f64],
    sample_phase: &mut usize,
    on_frame: impl FnMut([f64; 28], bool),
) -> bool {
    use std::arch::x86_64::_mm256_storeu_pd;
    advance_tol_chunk(
        chunk,
        sample_phase,
        |sample, emit| {
            if !emit {
                for state in groups.iter_mut() {
                    state.advance(sample);
                }
                return None;
            }
            let mut frame = [0.0; 28];
            for (group, state) in groups.iter_mut().enumerate() {
                let intensity = state.advance(sample);
                let mut lanes = [0.0; 4];
                _mm256_storeu_pd(lanes.as_mut_ptr(), intensity);
                for lane in 0..4 {
                    frame[group * 4 + lane] = intensity_to_db(lanes[lane]);
                }
            }
            Some(frame)
        },
        on_frame,
    )
}

/// Stateful 48 kHz ISO 532-1 time-varying loudness processor.
///
/// Push and flush allocate no memory and never enter Rayon. Output latency is
/// one 24-sample internal frame.
pub struct ZwtvStream {
    field: FieldType,
    tol: TolStage,
    nl: NlStage,
    tw: TwState,
    held_core: [f64; 21],
    has_held: bool,
    sample_phase: usize,
    emitted_internal: u64,
    pending: FrameFlags,
    flushed: bool,
}

impl ZwtvStream {
    pub fn new(field: FieldType) -> Self {
        let avx2 = crate::simd::use_avx2();
        let nl_b = nl_coeffs();
        Self {
            field,
            tol: new_tol_stage(avx2),
            nl: new_nl_stage(nl_b, avx2),
            tw: TwState::new(),
            held_core: [0.0; 21],
            has_held: false,
            sample_phase: 0,
            emitted_internal: 0,
            pending: FrameFlags::default(),
            flushed: false,
        }
    }

    pub fn reset(&mut self) {
        let Self {
            field: _,
            tol,
            nl,
            tw,
            held_core,
            has_held,
            sample_phase,
            emitted_internal,
            pending,
            flushed,
        } = self;
        match tol {
            TolStage::Scalar(states) => states.iter_mut().for_each(TolBandState::reset),
            #[cfg(target_arch = "x86_64")]
            TolStage::Avx2(groups) => {
                for state in groups.iter_mut() {
                    unsafe { state.reset() };
                }
            }
        }
        match nl {
            NlStage::Scalar { states, b: _ } => states.fill(NlBandState::default()),
            #[cfg(target_arch = "x86_64")]
            NlStage::Avx2 {
                groups,
                consts: _,
                tail,
                b: _,
            } => {
                for state in groups.iter_mut() {
                    *state = unsafe { super::nonlinear_decay::NlGroupState::zero() };
                }
                *tail = NlBandState::default();
            }
        }
        tw.reset();
        *held_core = [0.0; 21];
        *has_held = false;
        *sample_phase = 0;
        *emitted_internal = 0;
        *pending = FrameFlags::default();
        *flushed = false;
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
        let Self {
            field,
            tol,
            nl,
            tw,
            held_core,
            has_held,
            sample_phase,
            emitted_internal,
            pending,
            flushed: _,
        } = self;
        let mut written = 0;
        let mut on_frame = |frame, saw_nonfinite| {
            if saw_nonfinite {
                pending.insert(FrameFlags::NONFINITE_INPUT);
            }
            written += Self::on_internal_frame(
                *field,
                nl,
                tw,
                held_core,
                has_held,
                emitted_internal,
                pending,
                frame,
                &mut out[written..],
            );
        };
        let residual_nonfinite = match tol {
            TolStage::Scalar(states) => {
                advance_tol_scalar_chunk(states, chunk, sample_phase, &mut on_frame)
            }
            #[cfg(target_arch = "x86_64")]
            TolStage::Avx2(groups) => unsafe {
                advance_tol_avx2_chunk(groups, chunk, sample_phase, &mut on_frame)
            },
        };
        if residual_nonfinite {
            pending.insert(FrameFlags::NONFINITE_INPUT);
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
        Self::emit_loudness(
            &mut self.nl,
            &mut self.tw,
            &mut self.emitted_internal,
            &mut self.pending,
            &held,
            &[0.0; 21],
            out,
        )
    }

    /// Return pending flags observed after the most recent output frame.
    /// Before flush the value is provisional and will be attached to the next
    /// output frame. Only after flush does it represent undelivered tail events.
    pub const fn residual_flags(&self) -> FrameFlags {
        self.pending
    }

    #[allow(clippy::too_many_arguments)]
    fn on_internal_frame(
        field: FieldType,
        nl: &mut NlStage,
        tw: &mut TwState,
        held_core: &mut [f64; 21],
        has_held: &mut bool,
        emitted_internal: &mut u64,
        pending: &mut FrameFlags,
        tol_db: [f64; 28],
        out: &mut [StreamFrame],
    ) -> usize {
        let (core, clamped) = main_loudness_clamped(&tol_db, field);
        if clamped {
            pending.insert(FrameFlags::CLAMPED_120DB);
        }
        let wrote = if *has_held {
            let held = *held_core;
            Self::emit_loudness(nl, tw, emitted_internal, pending, &held, &core, out)
        } else {
            0
        };
        *held_core = core;
        *has_held = true;
        wrote
    }

    fn emit_loudness(
        nl: &mut NlStage,
        tw: &mut TwState,
        emitted_internal: &mut u64,
        pending: &mut FrameFlags,
        held: &[f64; 21],
        next: &[f64; 21],
        out: &mut [StreamFrame],
    ) -> usize {
        let nl = advance_nl_stage(nl, held, next);
        let n = tw.advance(calc_slopes_n_only(&nl));
        let internal = *emitted_internal;
        *emitted_internal += 1;
        if !internal.is_multiple_of(OUT_DECIM as u64) {
            return 0;
        }
        let index = internal / OUT_DECIM as u64;
        let mut flags = pending.take();
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
    let avx2 = crate::simd::use_avx2();
    let (tol, n_time) = super::third_octave_levels::third_octave_levels_with_mode_and_backend(
        signal,
        super::ParMode::Sequential,
        avx2,
    );
    let mut core = vec![[0.0; 21]; n_time];
    for t in 0..n_time {
        let frame = std::array::from_fn(|band| tol[band * n_time + t]);
        core[t] = main_loudness_clamped(&frame, field).0;
    }
    let b = nl_coeffs();
    let mut nl = new_nl_stage(b, avx2);
    let mut tw = TwState::new();
    let mut out = Vec::with_capacity(n_time.div_ceil(OUT_DECIM));
    for t in 0..n_time {
        let next = if t + 1 < n_time {
            core[t + 1]
        } else {
            [0.0; 21]
        };
        let nl_frame = advance_nl_stage(&mut nl, &core[t], &next);
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
