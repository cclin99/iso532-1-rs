mod common;

use iso532::{simd, FieldType};

#[test]
fn forced_scalar_stream_matches_scalar_zerostate_reference() {
    simd::set_force_scalar(true);
    assert!(!simd::use_avx2());
    let signal = common::synth_signal();
    let reference = iso532::zwtv::stream::zwtv_reference_zerostate(&signal, FieldType::Free);
    let got = common::run_chunked(&signal, std::iter::once(signal.len()));
    assert_eq!(got.len(), reference.len());
    for (frame, expected) in got.iter().zip(reference) {
        assert_eq!(frame.n.to_bits(), expected.to_bits());
    }
    simd::set_force_scalar(false);
}
