//! F-01 regression gate: ISO 532-1 Annex A low-frequency level correction.
//!
//! Annex A (`corr_third_octave_intensities`) walks the eight RAP ranges with
//! `while (j < 7 && level > RAP[j] - DLL[j][band]) j++;` so a level above the
//! seventh threshold receives the last DLL row. MoSQITo 1.2.1 (and upstream
//! master as of 2026-10-31) vectorises that loop as `arange(1, 7)` and does
//! not reach the last row, leaving a 0 dB correction instead of DLL[7].
//! Finding F-01; this crate's current judgment is to follow Annex A. The
//! tests below pin that divergence against values from
//! the official ISO 532-1 Annex A C program (see
//! docs/F01-LOW-FREQ-DLL-ROW-FIX-2026-10-31.md for provenance).
//!
//! Self-contained: no golden data required.
#[allow(dead_code)]
mod common;

use iso532::core::calc_slopes::calc_slopes;
use iso532::core::main_loudness::main_loudness;
use iso532::{loudness_zwst, loudness_zwtv, FieldType, FrameFlags, N_WARMUP_FRAMES};

const FS: f64 = 48_000.0;

/// Annex B workbook acceptance: |got - ref| <= max(0.1, 0.05 * ref).
fn within_iso(got: f64, reference: f64) -> bool {
    (got - reference).abs() <= 0.1_f64.max(0.05 * reference.abs())
}

/// Official Annex A C program, 28-band stationary entry, band 0 = 118.000001 dB,
/// all other bands -60 dB, free field. CLI prints 52.51.
const C_REF_CORE_118_000001: f64 = 52.514908816;
/// Official Annex A C library, 2 s / 25 Hz / 119 dB SPL sine, stationary, free field.
const C_REF_ZWST_25HZ_119DB: f64 = 56.704172426;
/// Official Annex A C library, same sine, time-varying max loudness.
const C_REF_ZWTV_MAX_25HZ_119DB: f64 = 56.878693537;

/// 2 s sine at 25 Hz with the given dB SPL (RMS), in pascals.
fn sine_25hz(db_spl: f64) -> Vec<f64> {
    let amp = 20e-6 * 10f64.powf(db_spl / 20.0) * 2f64.sqrt();
    (0..2 * FS as usize)
        .map(|i| amp * (2.0 * std::f64::consts::PI * 25.0 * i as f64 / FS).sin())
        .collect()
}

fn core_n(band0_level: f64, field: FieldType) -> f64 {
    let mut spec = [-60.0; 28];
    spec[0] = band0_level;
    calc_slopes(&main_loudness(&spec, field).unwrap()).0
}

#[test]
fn core_band0_118_000001_db_matches_annex_a_reference() {
    let n = core_n(118.000001, FieldType::Free);
    assert!(
        within_iso(n, C_REF_CORE_118_000001),
        "N = {n} sone, Annex A C reference {C_REF_CORE_118_000001} (MoSQITo-rule value is 154.93)"
    );
}

#[test]
fn core_band0_threshold_118_db_is_strict_and_last_row_applies_above_it() {
    // 118 dB is RAP[6] - DLL[6][0]; at the threshold the seventh row (-18 dB)
    // still applies, one ULP above it the last row (-15 dB) applies. The
    // resulting 3 dB step must be small, not the 18 dB step of a missing row.
    let at = core_n(118.0, FieldType::Free);
    let above = core_n(118.0_f64.next_up(), FieldType::Free);
    assert!(above > at, "N must not decrease across the threshold");
    assert!(
        above / at < 1.5,
        "N jumped {at} -> {above} across 118 dB: last DLL row missing?"
    );
    // 120 dB is still inside the Annex A table (threshold for the last row is
    // 135 dB on band 0) and must be accepted; 120 + ULP is rejected.
    let mut spec = [-60.0; 28];
    spec[0] = 120.0;
    assert!(main_loudness(&spec, FieldType::Free).is_ok());
    spec[0] = 120.0_f64.next_up();
    assert!(main_loudness(&spec, FieldType::Free).is_err());
}

#[test]
fn core_diffuse_field_uses_the_same_row_selection() {
    // DDF only shifts the critical-band level; the DLL row choice is field
    // independent, so diffuse must land in the same tolerance window.
    let n = core_n(118.000001, FieldType::Diffuse);
    assert!(n < 70.0, "diffuse N = {n}: last DLL row missing?");
}

#[test]
fn zwst_25hz_119db_sine_matches_annex_a_reference() {
    let r = loudness_zwst(&sine_25hz(119.0), FS, FieldType::Free).unwrap();
    assert!(
        within_iso(r.n, C_REF_ZWST_25HZ_119DB),
        "ZWST N = {} sone, Annex A C reference {C_REF_ZWST_25HZ_119DB}",
        r.n
    );
}

#[test]
fn zwtv_25hz_119db_sine_max_matches_annex_a_reference() {
    let r = loudness_zwtv(&sine_25hz(119.0), FS, FieldType::Free).unwrap();
    let n_max = r.n.iter().cloned().fold(f64::MIN, f64::max);
    assert!(
        within_iso(n_max, C_REF_ZWTV_MAX_25HZ_119DB),
        "ZWTV max N = {n_max} sone, Annex A C reference {C_REF_ZWTV_MAX_25HZ_119DB}"
    );
}

#[test]
fn stream_25hz_119db_sine_matches_batch_and_is_not_clamped() {
    // The stream path reaches the same table through main_loudness_clamped;
    // 119 dB sits below the 120 dB clamp, so no CLAMPED flag may appear and the
    // post-warm-up maximum must agree with the Annex A reference.
    let signal = sine_25hz(119.0);
    let frames = common::run_chunked(&signal, std::iter::repeat(480));
    assert!(frames
        .iter()
        .all(|f| !f.flags.contains(FrameFlags::CLAMPED_120DB)));
    let n_max = frames
        .iter()
        .filter(|f| f.t_frame_index >= N_WARMUP_FRAMES)
        .map(|f| f.n)
        .fold(f64::MIN, f64::max);
    assert!(
        within_iso(n_max, C_REF_ZWTV_MAX_25HZ_119DB),
        "stream max N = {n_max} sone, Annex A C reference {C_REF_ZWTV_MAX_25HZ_119DB}"
    );
    // Since F-02 the batch path starts the nonlinear decay from zero state
    // like the stream, so the two must agree bitwise from frame 0 (before
    // F-02 the MoSQITo tail seed made this signal converge to <= 1e-9 only
    // from frame 597).
    let batch = loudness_zwtv(&signal, FS, FieldType::Free).unwrap();
    assert_eq!(batch.n.len(), frames.len());
    for (i, (b, f)) in batch.n.iter().zip(&frames).enumerate() {
        assert_eq!(
            b.to_bits(),
            f.n.to_bits(),
            "frame {i}: batch={b} stream={}",
            f.n
        );
    }
}
