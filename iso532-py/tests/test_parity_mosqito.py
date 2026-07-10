"""Parity umbrella: Rust binding vs mosqito 1.2.1 direct run (spec §9).

Runs ONLY in the local .venv (mosqito + data/annexb present); skips
cleanly elsewhere. This suite is the regression umbrella for every
phase after R3 — do not weaken tolerances to make a change pass.
Expected runtime: ~5-10 min (mosqito zwtv is ~0.45x realtime).
"""

import sys
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("mosqito")
from mosqito.sq_metrics import loudness_zwst, loudness_zwtv  # noqa: E402

import iso532  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
if not (ROOT / "data" / "annexb").is_dir():
    pytest.skip("data/annexb missing — run tools/setup_env.sh", allow_module_level=True)

sys.path.insert(0, str(ROOT / "tools"))
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


@pytest.fixture(scope="session")
def signals():
    return make_signals()


@pytest.mark.parametrize("name", NAMES)
def test_zwtv_parity(signals, name):
    sig = np.ascontiguousarray(signals[name], dtype=np.float64)
    want = loudness_zwtv(sig, float(FS))
    got = iso532.loudness_zwtv(sig, float(FS))
    for label, g, w in zip(("N", "N_specific", "bark"), got[:3], want[:3]):
        np.testing.assert_allclose(
            g,
            np.asarray(w, dtype=np.float64),
            rtol=RTOL,
            atol=ATOL,
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
def test_zwst_parity(signals, name):
    sig = np.ascontiguousarray(signals[name], dtype=np.float64)
    want_n, want_spec, want_bark = loudness_zwst(sig, float(FS))
    got_n, got_spec, got_bark = iso532.loudness_zwst(sig, float(FS))
    np.testing.assert_allclose(
        got_n, float(want_n), rtol=RTOL, atol=ATOL, err_msg=f"{name}/N"
    )
    np.testing.assert_allclose(
        got_spec,
        np.asarray(want_spec, dtype=np.float64).ravel(),
        rtol=RTOL,
        atol=ATOL,
        err_msg=f"{name}/N_specific",
    )
    np.testing.assert_allclose(
        got_bark, want_bark, rtol=RTOL, atol=ATOL, err_msg=f"{name}/bark"
    )
