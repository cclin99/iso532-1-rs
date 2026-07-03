mod common;
use common::*;
use iso532::core::calc_slopes::calc_slopes;
use iso532::core::main_loudness::main_loudness;
use iso532::zwst::{noct_spectrum_rms, spec_to_db};
use iso532::{loudness_zwst, FieldType, Iso532Error};

#[test]
fn noct_spectrum_matches_mosqito() {
    for sig in ["sine_1k_60", "sine_250_80", "white_60"] {
        let x = read_bin(sig, "sig.bin");
        let want = read_bin(sig, "spec_third_amp.bin");
        let got = noct_spectrum_rms(&x);
        assert_close(&got, &want, 1e-7, 1e-12, &format!("{sig}/noct"));
    }
}

#[test]
fn spec_to_db_matches_mosqito_amp2db() {
    for sig in ["sine_1k_60", "sine_250_80", "white_60"] {
        let spec = read_bin(sig, "spec_third_amp.bin");
        let want = read_bin(sig, "spec_third_db.bin");
        let got = spec_to_db(&spec);
        assert_close(&got, &want, 1e-12, 1e-12, &format!("{sig}/spec_to_db"));
    }
}

#[test]
fn main_loudness_matches_mosqito() {
    for sig in ["sine_1k_60", "sine_250_80", "sine_4k_60", "white_60"] {
        let spec_db = read_bin(sig, "spec_third_db.bin");
        let want = read_bin(sig, "nm_free.bin");
        let got = main_loudness(&spec_db, FieldType::Free).unwrap();
        assert_close(&got, &want, 1e-9, 1e-15, &format!("{sig}/nm free"));
        let want_d = read_bin(sig, "nm_diffuse.bin");
        let got_d = main_loudness(&spec_db, FieldType::Diffuse).unwrap();
        assert_close(&got_d, &want_d, 1e-9, 1e-15, &format!("{sig}/nm diffuse"));
    }
}

#[test]
fn main_loudness_rejects_over_120db() {
    let mut spec = vec![50.0; 28];
    spec[3] = 121.0;
    assert_eq!(
        main_loudness(&spec, FieldType::Free).unwrap_err(),
        Iso532Error::LevelExceeds120dB
    );
}

#[test]
fn calc_slopes_matches_mosqito() {
    for sig in ["sine_1k_60", "sine_250_80", "sine_4k_60", "white_60"] {
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

#[test]
fn zwst_end_to_end_matches_mosqito() {
    for sig in [
        "sine_1k_60",
        "sine_250_80",
        "sine_4k_60",
        "white_60",
        "annexb_sig3",
        "annexb_sig5",
    ] {
        let x = read_bin(sig, "sig.bin");
        let want_n = read_bin(sig, "N.bin")[0];
        let want_spec = read_bin(sig, "N_specific.bin");
        let r = loudness_zwst(&x, 48000.0, FieldType::Free).unwrap();
        assert!(
            (r.n - want_n).abs() <= 1e-3 + 1e-6 * want_n.abs(),
            "{sig}: N {} vs {want_n}",
            r.n
        );
        assert_close(
            &r.n_specific,
            &want_spec,
            1e-6,
            1e-9,
            &format!("{sig}/spec"),
        );
        assert_eq!(r.bark_axis.len(), 240);
    }
}
