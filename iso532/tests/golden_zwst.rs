//! MoSQITo 1.2.1 goldens. The stage tests (noct spectrum, dB conversion, main
//! loudness) stay tight. Since 0.4.0 the slope stage follows ISO 532-1 Annex A
//! (F-04 no per-frame rounding, F-05 band completion) and the correctness
//! reference is the Annex A C golden (`tests/golden_c.rs`); the total
//! loudness comparisons below are a compatibility check against MoSQITo
//! (相容性對照) with the D-E bound of 5e-3 sone (phase plan 0.4.0). Since F-07
//! (Annex A writes the core loudness, or the segment that contains the
//! sample, in the cell where a slope ends) the specific loudness differs from
//! MoSQITo by up to ~4e-2 sone/Bark by design; it is recorded, not gated (D-H).

mod common;
use common::*;

/// MoSQITo compatibility bound for the total loudness (D-E, D-H), sone.
const COMPAT_TOL: f64 = 5e-3;
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
fn calc_slopes_compat_mosqito() {
    for sig in ["sine_1k_60", "sine_250_80", "sine_4k_60", "white_60"] {
        let nm_v = read_bin(sig, "nm_free.bin");
        let nm: [f64; 21] = nm_v.as_slice().try_into().unwrap();
        let want_n = read_bin(sig, "N.bin")[0];
        let want_spec = read_bin(sig, "N_specific.bin");
        let (n, spec) = calc_slopes(&nm);
        assert!(
            (n - want_n).abs() <= COMPAT_TOL,
            "{sig}: N {n} vs {want_n} (compatibility)"
        );
        record_max_abs_diff(&spec, &want_spec, &format!("{sig}/N_specific vs MoSQITo"));
    }
}

#[test]
fn zwst_end_to_end_compat_mosqito() {
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
            (r.n - want_n).abs() <= COMPAT_TOL,
            "{sig}: N {} vs {want_n} (compatibility)",
            r.n
        );
        record_max_abs_diff(&r.n_specific, &want_spec, &format!("{sig}/spec vs MoSQITo"));
        assert_eq!(r.bark_axis.len(), 240);
    }
}
