mod common;

use iso532::{simd, FieldType, StreamFrame, ZwtvStream};

#[test]
fn forced_scalar_stream_matches_scalar_zerostate_reference() {
    simd::set_force_scalar(true);
    assert!(!simd::use_avx2());
    let signal = common::synth_signal();
    let reference = iso532::zwtv::stream::zwtv_reference_zerostate(&signal, FieldType::Free);
    let mut stream = ZwtvStream::new(FieldType::Free);
    let mut out = vec![StreamFrame::default(); ZwtvStream::max_frames_for_chunk(signal.len())];
    let mut got = Vec::new();
    let n = stream.push(&signal, &mut out);
    got.extend_from_slice(&out[..n]);
    let n = stream.flush(&mut out);
    got.extend_from_slice(&out[..n]);
    assert_eq!(got.len(), reference.len());
    for (frame, expected) in got.iter().zip(reference) {
        assert_eq!(frame.n.to_bits(), expected.to_bits());
    }
    simd::set_force_scalar(false);
}
