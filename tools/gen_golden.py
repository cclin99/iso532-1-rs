"""Generate per-stage golden data from mosqito 1.2.1 for the Rust port.

Output layout: data/golden/<name>/<stage>.bin  (little-endian f64, C order)
plus meta.json with array shapes.
Run: .venv/Scripts/python tools/gen_golden.py
"""
import json
from pathlib import Path

import numpy as np
from scipy.signal import cheby1, sosfilt, sosfiltfilt, decimate

from mosqito.sound_level_meter import noct_spectrum
from mosqito.utils import amp2db
from mosqito.utils import load
from mosqito.sq_metrics.loudness.loudness_zwst._main_loudness import _main_loudness
from mosqito.sq_metrics.loudness.loudness_zwst._calc_slopes import _calc_slopes
from mosqito.sq_metrics.loudness.loudness_zwtv._third_octave_levels import _third_octave_levels
from mosqito.sq_metrics.loudness.loudness_zwtv._nonlinear_decay import _nl_loudness
from mosqito.sq_metrics.loudness.loudness_zwtv._temporal_weighting import _temporal_weighting

FS = 48000
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "golden"


def dump(d: Path, name: str, arr):
    arr = np.ascontiguousarray(np.asarray(arr, dtype="<f8"))
    arr.tofile(d / f"{name}.bin")
    return list(arr.shape)


def sine(freq, db, dur):
    t = np.arange(0, dur, 1 / FS)
    p_rms = 2e-5 * 10 ** (db / 20)
    return np.sqrt(2) * p_rms * np.sin(2 * np.pi * freq * t)


def make_signals():
    rng = np.random.default_rng(532)
    sigs = {
        "sine_1k_60": sine(1000, 60, 1.0),
        "sine_250_80": sine(250, 80, 1.0),
        "sine_4k_60": sine(4000, 60, 1.0),
        "white_60": None,
        "pulse_1k_70": None,
        "step_60_80": None,
    }
    w = rng.standard_normal(FS)
    w *= (2e-5 * 10 ** (60 / 20)) / np.sqrt(np.mean(w**2))
    sigs["white_60"] = w
    p = np.zeros(FS)
    burst = sine(1000, 70, 0.01)
    p[24000 : 24000 + len(burst)] = burst
    sigs["pulse_1k_70"] = p
    s = np.concatenate([sine(1000, 60, 0.5), sine(1000, 80, 0.5)])
    sigs["step_60_80"] = s
    # Annex B wav files (loaded exactly as mosqito tests do)
    for wav, key in [
        ("Test signal 3 (1 kHz 60 dB).wav", "annexb_sig3"),
        ("Test signal 5 (pinknoise 60 dB).wav", "annexb_sig5"),
        ("Test signal 10 (tone pulse 1 kHz 10 ms 70 dB).wav", "annexb_sig10"),
    ]:
        path = ROOT / "data" / "annexb" / wav
        if path.exists():
            sig, fs = load(str(path), wav_calib=2 * 2**0.5)
            assert fs == FS, f"{wav}: fs={fs}"
            sigs[key] = sig
    return sigs


def golden_zwst(d, sig, meta):
    spec_amp, _ = noct_spectrum(sig, FS, fmin=24, fmax=12600)
    meta["spec_third_amp"] = dump(d, "spec_third_amp", spec_amp)
    spec_db = amp2db(np.copy(spec_amp), ref=2e-5)
    meta["spec_third_db"] = dump(d, "spec_third_db", spec_db)
    nm = _main_loudness(spec_db, "free")
    meta["nm_free"] = dump(d, "nm_free", nm)
    nm_d = _main_loudness(spec_db, "diffuse")
    meta["nm_diffuse"] = dump(d, "nm_diffuse", nm_d)
    n, n_spec = _calc_slopes(nm)
    meta["N"] = dump(d, "N", np.atleast_1d(n))
    meta["N_specific"] = dump(d, "N_specific", n_spec)


def golden_zwtv(d, sig, meta):
    tol, time_axis, _ = _third_octave_levels(sig, FS)
    meta["third_octave_level"] = dump(d, "third_octave_level", tol)
    core = _main_loudness(tol, "free")
    meta["core_loudness"] = dump(d, "core_loudness", core)
    nl = _nl_loudness(np.copy(core))
    meta["nl_loudness"] = dump(d, "nl_loudness", nl)
    loud, spec_loud = _calc_slopes(nl)
    meta["loudness_raw"] = dump(d, "loudness_raw", loud)
    meta["spec_loudness_raw"] = dump(d, "spec_loudness_raw", spec_loud)
    filt = _temporal_weighting(loud)
    meta["filt_loudness"] = dump(d, "filt_loudness", filt)
    meta["N_time"] = dump(d, "N_time", filt[::4])
    meta["N_spec_time"] = dump(d, "N_spec_time", spec_loud[:, ::4])
    meta["time_axis"] = dump(d, "time_axis", time_axis[::4])


def golden_dsp(d, meta):
    """Unit-level DSP goldens: sosfilt / sosfiltfilt / decimate on a fixed input."""
    rng = np.random.default_rng(1)
    x = rng.standard_normal(4096)
    meta["dsp_x"] = dump(d, "dsp_x", x)
    sos = cheby1(8, 0.05, 0.8 / 10, output="sos")
    meta["dsp_cheby_sos"] = dump(d, "dsp_cheby_sos", sos)
    meta["dsp_sosfilt_y"] = dump(d, "dsp_sosfilt_y", sosfilt(sos, x))
    meta["dsp_sosfiltfilt_y"] = dump(d, "dsp_sosfiltfilt_y", sosfiltfilt(sos, x))
    meta["dsp_decimate_q10"] = dump(d, "dsp_decimate_q10", decimate(x, 10))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d = OUT / "_dsp"
    d.mkdir(exist_ok=True)
    meta = {}
    golden_dsp(d, meta)
    (d / "meta.json").write_text(json.dumps(meta))

    for name, sig in make_signals().items():
        if sig is None:
            continue
        d = OUT / name
        d.mkdir(exist_ok=True)
        meta = {"fs": FS}
        meta["sig"] = dump(d, "sig", sig)
        golden_zwst(d, sig, meta)
        golden_zwtv(d, sig, meta)
        (d / "meta.json").write_text(json.dumps(meta))
        print("done", name)


if __name__ == "__main__":
    main()