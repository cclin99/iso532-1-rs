mod common;
use common::*;
use iso532::core::calc_slopes::calc_slopes;
use iso532::core::main_loudness::main_loudness;
use iso532::{FieldType, Iso532Error};

const SIGNALS: [&str; 4] = ["sine_1k_60", "sine_250_80", "sine_4k_60", "white_60"];

#[test]
fn main_loudness_matches_mosqito_free_and_diffuse_core_loudness() {
    for sig in SIGNALS {
        let spec = read_bin(sig, "spec_third_db.bin");
        let got = main_loudness(&spec, FieldType::Free).unwrap();
        let want = read_bin(sig, "nm_free.bin");
        assert_close(&got, &want, 1e-9, 1e-15, &format!("{sig}/nm free"));

        let got_d = main_loudness(&spec, FieldType::Diffuse).unwrap();
        let want_d = read_bin(sig, "nm_diffuse.bin");
        assert_close(&got_d, &want_d, 1e-9, 1e-15, &format!("{sig}/nm diffuse"));
    }
}

#[test]
fn main_loudness_rejects_low_frequency_third_octave_level_above_120_db() {
    let mut spec = vec![50.0; 28];
    spec[3] = 121.0;
    assert_eq!(
        main_loudness(&spec, FieldType::Free).unwrap_err(),
        Iso532Error::LevelExceeds120dB
    );
}

#[test]
fn calc_slopes_matches_mosqito_total_and_specific_loudness() {
    for sig in SIGNALS {
        let nm_v = read_bin(sig, "nm_free.bin");
        let nm: [f64; 21] = nm_v.as_slice().try_into().unwrap();
        let want_n = read_bin(sig, "N.bin")[0];
        let want_spec = read_bin(sig, "N_specific.bin");
        let (n, spec) = calc_slopes(&nm);
        assert!(
            (n - want_n).abs() <= 1e-9 + 1e-6 * want_n.abs(),
            "{sig}: N {n} vs {want_n}"
        );
        assert_close(&spec, &want_spec, 1e-6, 1e-9, &format!("{sig}/N_specific"));
    }
}
