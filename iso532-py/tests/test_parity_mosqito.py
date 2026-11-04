"""Parity umbrella: Rust binding vs mosqito 1.2.1 direct run (spec §9).

Runs ONLY in the local .venv (mosqito + data/annexb present); skips
cleanly elsewhere. This suite is the regression umbrella for every
phase after R3 — do not weaken tolerances to make a change pass.
Expected runtime: ~5-10 min (mosqito zwtv is ~0.45x realtime).

0.4.0: the slope stage follows ISO 532-1 Annex A (F-04 no per-frame rounding
of the total, F-05 band completion, F-07 specific value in the cell where a
slope segment ends); the correctness reference is the Annex A C golden
(iso532/tests/golden_c.rs). Per decisions D-E / D-H of the 0.4.0 phase plan
the total loudness is compared with MoSQITo as a compatibility check
(COMPAT_ATOL = 5e-3 sone). Specific loudness (time-varying and stationary)
differs from MoSQITo by design since F-07 (Annex A writes the core loudness,
or the segment that contains the sample, where MoSQITo extrapolates the
slope; up to ~4e-2 sone/Bark): it is recorded (maximum printed, finiteness
and shape asserted), not gated. The Bark axis keeps RTOL/ATOL.
"""

from pathlib import Path

import numpy as np
import pytest

from conftest import REQUIRE_PARITY

if REQUIRE_PARITY:
    import mosqito  # noqa: F401
    import iso532
else:
    pytest.importorskip("mosqito")
    iso532 = pytest.importorskip("iso532")
from mosqito.sq_metrics import loudness_zwst, loudness_zwtv  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
if not (ROOT / "data" / "annexb").is_dir():
    if REQUIRE_PARITY:
        raise RuntimeError("ISO532_REQUIRE_PARITY=1 but data/annexb missing")
    pytest.skip("data/annexb missing — run tools/setup_env.sh", allow_module_level=True)

from gen_golden import FS, make_signals  # noqa: E402

NAMES = [
    "sine_1k_60",
    "sine_250_80",
    "sine_4k_60",
    "white_60",
    "pulse_1k_70",
    "step_60_80",
    "annexb_sig3",
    "annexb_sig5",
    "annexb_sig10",
]

RTOL, ATOL = 1e-6, 1e-9
COMPAT_ATOL = 5e-3  # N vs MoSQITo since 0.4.0 (D-E, D-H)


def tol(label):
    return (0.0, COMPAT_ATOL) if label == "N" else (RTOL, ATOL)


def record_specific(got, want, ctx):
    """Record-only N_specific comparison (D-H): shape and finiteness asserted,
    maximum |got - want| printed (run pytest with -s to see it), not gated."""
    got = np.asarray(got, dtype=np.float64)
    want = np.asarray(want, dtype=np.float64)
    assert got.shape == want.shape, f"{ctx}: shape {got.shape} vs {want.shape}"
    assert np.all(np.isfinite(got)), f"{ctx}: result not finite"
    assert np.all(np.isfinite(want)), f"{ctx}: MoSQITo reference not finite"
    diff = np.abs(got - want)
    worst = float(diff.max()) if diff.size else 0.0
    print(f"{ctx}: max |diff| {worst:.3e} vs MoSQITo (recorded, not gated)")
    return worst


@pytest.fixture(scope="session")
def signals():
    return make_signals()


@pytest.fixture(scope="session")
def mosqito_runs():
    """MoSQITo results shared by the split parity tests (MoSQITo zwtv is slow)."""
    return {}


def mosqito_zwtv(runs, key, sig):
    if key not in runs:
        runs[key] = loudness_zwtv(sig, float(FS))
    return runs[key]


@pytest.mark.parametrize("name", NAMES)
def test_zwtv_parity(signals, mosqito_runs, name):
    # MoSQITo seeds its nonlinear decay from the last frame (F-02); the exact
    # comparison therefore runs the binding with nl_init="mosqito_tail".
    sig = np.ascontiguousarray(signals[name], dtype=np.float64)
    want = mosqito_zwtv(mosqito_runs, name, sig)
    got = iso532.loudness_zwtv(sig, float(FS), nl_init="mosqito_tail")
    for label, g, w in (("N", got[0], want[0]), ("bark", got[2], want[2])):
        rtol, atol = tol(label)
        np.testing.assert_allclose(
            g,
            np.asarray(w, dtype=np.float64),
            rtol=rtol,
            atol=atol,
            err_msg=f"{name}/{label}",
        )

    # mosqito 1.2.1 constructs its axis with linspace(0, duration, n_time),
    # including the signal endpoint and therefore producing a duration-dependent
    # step slightly larger than 2 ms. The Rust API follows the ISO output grid,
    # which is independently checked against Annex B and frozen bitwise in the
    # smoke suite. Keep the parity umbrella focused on computed loudness values.
    got_time = got[3]
    iso_time = (
        np.arange(got_time.size, dtype=np.uint64) * np.uint64(96)
    ).astype(np.float64) / float(FS)
    np.testing.assert_array_equal(got_time, iso_time)


@pytest.mark.parametrize("name", NAMES)
def test_zwtv_specific_parity(signals, mosqito_runs, name):
    sig = np.ascontiguousarray(signals[name], dtype=np.float64)
    want = mosqito_zwtv(mosqito_runs, name, sig)
    got = iso532.loudness_zwtv(sig, float(FS), nl_init="mosqito_tail")
    record_specific(got[1], want[1], f"{name}/N_specific zwtv")


# 0.5 s of trailing silence drives every band's core loudness to exactly zero
# (measured: at most 0.177 s needed on these fixtures), which makes MoSQITo's
# last-frame seed exactly zero.
SILENT_TAIL = np.zeros(FS // 2, dtype=np.float64)


@pytest.mark.parametrize("name", NAMES)
def test_zwtv_default_matches_mosqito_given_a_silent_tail(signals, mosqito_runs, name):
    """Cross-check of the F-02 default against MoSQITo's own arithmetic.

    Appending silence to MoSQITo's input zeroes its seed, so MoSQITo on
    (signal + silence) must equal the zero-state default on (signal) for every
    output frame that only depends on the original samples: all frames of the
    unpadded result, because the last third-octave frame (whose look-ahead
    differs) is not an output frame of the decimated grid.
    """
    sig = np.ascontiguousarray(signals[name], dtype=np.float64)
    padded = np.concatenate([sig, SILENT_TAIL])
    want = mosqito_zwtv(mosqito_runs, f"{name}+silence", padded)
    got = iso532.loudness_zwtv(sig, float(FS))
    frames = got[0].shape[0]
    # last output frame k=frames-1 reads nl frame 4(k); nl frames 0..n-2 are
    # tail-independent (frame n-1 looks ahead into the padding)
    assert (frames - 1) * 4 <= sig.shape[0] // 24 - 2
    np.testing.assert_allclose(
        got[0], np.asarray(want[0], dtype=np.float64)[:frames],
        rtol=0.0, atol=COMPAT_ATOL, err_msg=f"{name}/N default",
    )


@pytest.mark.parametrize("name", NAMES)
def test_zwtv_default_specific_matches_mosqito_given_a_silent_tail(
    signals, mosqito_runs, name
):
    """N_specific half of the silent-tail cross-check (recorded, D-H)."""
    sig = np.ascontiguousarray(signals[name], dtype=np.float64)
    padded = np.concatenate([sig, SILENT_TAIL])
    want = mosqito_zwtv(mosqito_runs, f"{name}+silence", padded)
    got = iso532.loudness_zwtv(sig, float(FS))
    frames = got[0].shape[0]
    record_specific(
        got[1],
        np.asarray(want[1], dtype=np.float64)[:, :frames],
        f"{name}/N_specific zwtv default",
    )


@pytest.mark.parametrize("name", NAMES)
def test_zwst_parity(signals, name):
    sig = np.ascontiguousarray(signals[name], dtype=np.float64)
    want_n, want_spec, want_bark = loudness_zwst(sig, float(FS))
    got_n, got_spec, got_bark = iso532.loudness_zwst(sig, float(FS))
    np.testing.assert_allclose(
        got_n, float(want_n), rtol=0.0, atol=COMPAT_ATOL, err_msg=f"{name}/N"
    )
    record_specific(
        got_spec,
        np.asarray(want_spec, dtype=np.float64).ravel(),
        f"{name}/N_specific zwst",
    )
    np.testing.assert_allclose(
        got_bark, want_bark, rtol=RTOL, atol=ATOL, err_msg=f"{name}/bark"
    )
