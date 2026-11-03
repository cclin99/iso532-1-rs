//! F-02 regression gate: the batch nonlinear temporal decay starts from zero
//! state, as in the ISO 532-1 Annex A C program (`UoLast = U2Last = 0` per
//! band), so the batch output for a signal prefix cannot depend on what comes
//! after it.
//!
//! MoSQITo 1.2.1 vectorises the decay over the whole signal and its first
//! column reads column `-1`, which seeds every band with `core[-1] / 24`. The
//! Rust batch path reproduced that seed until this gate was added (finding
//! F-02, 2026-10-31; current judgment: follow Annex A). That seed is still
//! reachable through `NlInit::MosqitoTail` for golden comparisons, and the
//! reproduction numbers from the audit report are pinned below so that the
//! two initialisations stay distinguishable.
//!
//! Self-contained: no golden data, runs in CI.

mod common;

use iso532::zwtv::NlInit;
use iso532::{loudness_zwtv, FieldType, ZwtvProcessor, ZwtvStream};

const FS: f64 = 48_000.0;
const DEC: usize = 24; // third-octave frame hop
const OUT_DECIM: usize = 4; // output hop in third-octave frames

fn tone(freq: f64, db: f64, len: usize) -> Vec<f64> {
    let amp = 2e-5 * 10f64.powf(db / 20.0) * 2f64.sqrt();
    (0..len)
        .map(|i| amp * (2.0 * std::f64::consts::PI * freq * i as f64 / FS).sin())
        .collect()
}

fn lcg_noise(len: usize, amp: f64) -> Vec<f64> {
    let mut s = 0x9e37_79b9_7f4a_7c15_u64;
    (0..len)
        .map(|_| {
            s = s
                .wrapping_mul(6_364_136_223_846_793_005)
                .wrapping_add(1_442_695_040_888_963_407);
            ((s >> 11) as f64 / (1u64 << 53) as f64 * 2.0 - 1.0) * amp
        })
        .collect()
}

fn concat(prefix: &[f64], tail: &[f64]) -> Vec<f64> {
    let mut v = prefix.to_vec();
    v.extend_from_slice(tail);
    v
}

/// Output frames whose value is fully determined by the first `prefix_len`
/// samples: the nonlinear decay interpolates towards the *next* third-octave
/// frame, so the last prefix frame is excluded, and the temporal weighting is
/// causal. Everything else in the pipeline is causal as well.
fn determined_output_frames(prefix_len: usize) -> usize {
    let prefix_frames = prefix_len / DEC;
    (prefix_frames - 1).div_ceil(OUT_DECIM)
}

fn assert_prefix_bitwise(
    a: &iso532::LoudnessTimeVarying,
    b: &iso532::LoudnessTimeVarying,
    frames: usize,
    ctx: &str,
) {
    assert!(
        a.n.len() >= frames && b.n.len() >= frames,
        "{ctx}: too short"
    );
    for k in 0..frames {
        assert_eq!(
            a.n[k].to_bits(),
            b.n[k].to_bits(),
            "{ctx}: N frame {k}: {} vs {}",
            a.n[k],
            b.n[k]
        );
    }
    let (fa, fb) = (a.n.len(), b.n.len());
    for bark in 0..240 {
        for k in 0..frames {
            assert_eq!(
                a.n_specific[bark * fa + k].to_bits(),
                b.n_specific[bark * fb + k].to_bits(),
                "{ctx}: N' bark {bark} frame {k}"
            );
        }
    }
}

#[test]
fn batch_prefix_is_invariant_to_the_future_tail() {
    // The audit counterexample (silent prefix) plus a tonal prefix, each against
    // tails of different content and length.
    let prefixes: [(&str, Vec<f64>); 2] = [
        ("silence", vec![0.0; 24_000]),
        ("440Hz/60dB", tone(440.0, 60.0, 24_000)),
    ];
    let tails: [(&str, Vec<f64>); 4] = [
        ("silence", vec![0.0; 24_000]),
        ("1kHz/80dB", tone(1_000.0, 80.0, 24_000)),
        ("noise", lcg_noise(24_000, 0.2)),
        ("long 4kHz/75dB", tone(4_000.0, 75.0, 72_000)),
    ];
    let frames = determined_output_frames(24_000);
    assert_eq!(frames, 250, "0.5 s prefix determines 250 output frames");
    for (pname, prefix) in &prefixes {
        let reference = loudness_zwtv(&concat(prefix, &tails[0].1), FS, FieldType::Free).unwrap();
        for (tname, tail) in &tails[1..] {
            let got = loudness_zwtv(&concat(prefix, tail), FS, FieldType::Free).unwrap();
            assert_prefix_bitwise(&got, &reference, frames, &format!("{pname} + {tname}"));
        }
    }
}

#[test]
fn silent_prefix_yields_exactly_zero_loudness_before_the_tone_starts() {
    let signal = concat(&vec![0.0; 24_000], &tone(1_000.0, 80.0, 24_000));
    let r = loudness_zwtv(&signal, FS, FieldType::Free).unwrap();
    let frames = determined_output_frames(24_000);
    for k in 0..frames {
        assert_eq!(
            r.n[k].to_bits(),
            0.0f64.to_bits(),
            "N frame {k} = {}",
            r.n[k]
        );
    }
    for bark in 0..240 {
        for k in 0..frames {
            let v = r.n_specific[bark * r.n.len() + k];
            assert_eq!(
                v.to_bits(),
                0.0f64.to_bits(),
                "N' bark {bark} frame {k} = {v}"
            );
        }
    }
    // and the tone is still measured afterwards
    assert!(r.n.iter().cloned().fold(0.0, f64::max) > 10.0);
}

#[test]
fn batch_matches_the_causal_stream_bitwise_from_frame_zero() {
    let one_second = common::synth_signal();
    let cyclic: Vec<f64> = one_second.iter().copied().cycle().take(144_000).collect();
    let counterexample = concat(&vec![0.0; 24_000], &tone(1_000.0, 80.0, 24_000));
    for (name, signal) in [("synth x3", cyclic), ("silence+tone", counterexample)] {
        let batch = loudness_zwtv(&signal, FS, FieldType::Free).unwrap();
        let frames = common::run_chunked(&signal, std::iter::repeat(480));
        assert_eq!(batch.n.len(), frames.len(), "{name}: frame count");
        for (i, (b, f)) in batch.n.iter().zip(&frames).enumerate() {
            assert_eq!(
                b.to_bits(),
                f.n.to_bits(),
                "{name} frame {i}: batch={b} stream={}",
                f.n
            );
        }
    }
    let _ = ZwtvStream::latency_samples();
}

#[test]
fn processor_reuse_does_not_leak_state_between_calls() {
    let a = concat(&tone(440.0, 60.0, 24_000), &tone(1_000.0, 80.0, 24_000));
    let b = concat(&vec![0.0; 24_000], &lcg_noise(48_000, 0.1));
    let mut processor = ZwtvProcessor::new();
    let _ = processor.process(&a, FS, FieldType::Free).unwrap();
    let reused = processor.process(&b, FS, FieldType::Free).unwrap();
    let fresh = loudness_zwtv(&b, FS, FieldType::Free).unwrap();
    assert_eq!(reused.n.len(), fresh.n.len());
    assert_prefix_bitwise(&reused, &fresh, fresh.n.len(), "reuse");
}

#[test]
fn mosqito_tail_init_reproduces_the_audited_pre_fix_numbers() {
    // docs/修正報告.md §4.2: identical silent first half, 1 kHz / 80 dB second
    // half: pre-fix batch N[0] = 0.001623810180 sone and the first 0.25 s differ
    // from the all-silent signal by 0.113550559256 sone. Those numbers belong to
    // the MoSQITo tail seed and must stay reachable under `NlInit::MosqitoTail`.
    //
    // They were measured with the per-frame rounding of the total to 0.001 sone
    // that 0.4.0 removed (F-04). The rounding moves each frame by at most half a
    // step, 5e-4 sone, and temporal weighting is a convex smoother, so the audited
    // values must still hold within 5e-4 (one series) / 1e-3 (difference of two
    // series). The 0.4.0 values themselves are pinned to 1e-9.
    const AUDITED_N0: f64 = 0.001_623_810_180;
    const AUDITED_PREFIX_DIFF: f64 = 0.113_550_559_256;
    const N0: f64 = 0.001_623_699_865_834_095;
    const PREFIX_DIFF: f64 = 0.113_590_159_483_987;
    let silent = vec![0.0; 48_000];
    let signal = concat(&vec![0.0; 24_000], &tone(1_000.0, 80.0, 24_000));
    let mut p = ZwtvProcessor::new();
    let a = p
        .process_with(&silent, FS, FieldType::Free, NlInit::MosqitoTail)
        .unwrap();
    let b = p
        .process_with(&signal, FS, FieldType::Free, NlInit::MosqitoTail)
        .unwrap();
    assert!((b.n[0] - N0).abs() < 1e-9, "N[0] = {}", b.n[0]);
    assert!(
        (b.n[0] - AUDITED_N0).abs() <= 5e-4,
        "N[0] = {} vs audited {AUDITED_N0}",
        b.n[0]
    );
    let prefix_diff = a.n[..125]
        .iter()
        .zip(&b.n[..125])
        .map(|(x, y)| (x - y).abs())
        .fold(0.0, f64::max);
    assert!(
        (prefix_diff - PREFIX_DIFF).abs() < 1e-9,
        "prefix diff = {prefix_diff}"
    );
    assert!(
        (prefix_diff - AUDITED_PREFIX_DIFF).abs() <= 1e-3,
        "prefix diff = {prefix_diff} vs audited {AUDITED_PREFIX_DIFF}"
    );
    // The default is the zero state.
    let z = p.process(&signal, FS, FieldType::Free).unwrap();
    assert_eq!(z.n[0].to_bits(), 0.0f64.to_bits());
    assert_eq!(
        z.n,
        p.process_with(&signal, FS, FieldType::Free, NlInit::Zero)
            .unwrap()
            .n
    );
}

#[test]
fn both_initialisations_agree_when_the_signal_ends_in_silence() {
    // A silent tail makes the MoSQITo seed exactly zero, so the two paths must
    // be bitwise identical; this pins the fact that the seed is the only
    // difference between them.
    let signal = concat(&tone(1_000.0, 70.0, 24_000), &vec![0.0; 24_000]);
    let mut p = ZwtvProcessor::new();
    let zero = p.process(&signal, FS, FieldType::Free).unwrap();
    let tail = p
        .process_with(&signal, FS, FieldType::Free, NlInit::MosqitoTail)
        .unwrap();
    assert_prefix_bitwise(&zero, &tail, zero.n.len(), "silent tail");
}
