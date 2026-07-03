mod common;
use common::*;
use iso532::dsp::filtfilt::{decimate, sosfiltfilt};
use iso532::dsp::sos::{sosfilt, Sos};

fn cheby_sos_from_golden() -> Vec<Sos> {
    let raw = read_bin("_dsp", "dsp_cheby_sos.bin");
    raw.chunks_exact(6)
        .map(|c| Sos {
            b: [c[0], c[1], c[2]],
            a: [c[4], c[5]],
        })
        .collect()
}

#[test]
fn sosfilt_matches_scipy() {
    let x = read_bin("_dsp", "dsp_x.bin");
    let want = read_bin("_dsp", "dsp_sosfilt_y.bin");
    let mut y = x.clone();
    sosfilt(&cheby_sos_from_golden(), &mut y);
    assert_close(&y, &want, 1e-12, 1e-15, "sosfilt");
}

#[test]
fn sosfiltfilt_matches_scipy() {
    let x = read_bin("_dsp", "dsp_x.bin");
    let want = read_bin("_dsp", "dsp_sosfiltfilt_y.bin");
    let y = sosfiltfilt(&cheby_sos_from_golden(), &x);
    assert_close(&y, &want, 1e-9, 1e-12, "sosfiltfilt");
}

#[test]
fn decimate_matches_scipy() {
    let x = read_bin("_dsp", "dsp_x.bin");
    let want = read_bin("_dsp", "dsp_decimate_q10.bin");
    let y = decimate(&x, 10);
    assert_close(&y, &want, 1e-9, 1e-12, "decimate q=10");
}
