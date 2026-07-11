"""Smoke + cross-language bitwise contract tests (no mosqito; runs in CI)."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from iso532_testkit import contract_signal, fnv1a_f64  # noqa: E402

import iso532  # noqa: E402

FS = 48000.0

# Frozen from Rust:
#   cd iso532 && cargo test --test py_contract_dump -- --ignored --nocapture
# n/time_axis are bitwise-stable across platforms and backends (see
# docs/CI-HASH-GATE-DEBUG-2026-07-10.md). Values MUST come from an actual
# dump run — never invented, never copied from another signal.
N_HASH = 0x44E6822074554786
TIME_HASH = 0xF076BCB342595537


def test_zwtv_shapes_and_axes():
    n, spec, bark, time = iso532.loudness_zwtv(contract_signal(), FS)
    assert n.shape == (500,)
    assert time.shape == (500,)
    assert spec.shape == (240, 500)
    assert bark.shape == (240,)
    assert bark[0] == pytest.approx(0.1)
    assert bark[-1] == pytest.approx(24.0)
    assert np.all(np.isfinite(n)) and np.all(n >= 0)


def test_zwtv_diffuse_accepted():
    n, _spec, _bark, _time = iso532.loudness_zwtv(contract_signal(), FS, "diffuse")
    assert n.shape == (500,)


def test_zwst_shapes():
    n, spec, bark = iso532.loudness_zwst(contract_signal(), FS)
    assert isinstance(n, float) and n > 0
    assert spec.shape == (240,)
    assert bark.shape == (240,)


def test_bitwise_contract_n_and_time_axis():
    n, _spec, _bark, time = iso532.loudness_zwtv(contract_signal(), FS)
    assert hex(fnv1a_f64(n)) == hex(N_HASH)
    assert hex(fnv1a_f64(time)) == hex(TIME_HASH)


def test_error_mapping():
    sig = contract_signal()
    with pytest.raises(ValueError, match="48000"):
        iso532.loudness_zwtv(sig, 44100.0)
    with pytest.raises(ValueError, match="too short"):
        iso532.loudness_zwtv(sig[:100].copy(), FS)
    with pytest.raises(ValueError, match="field_type"):
        iso532.loudness_zwtv(sig, FS, "FREE")


def test_strict_input_contract():
    sig = contract_signal()
    with pytest.raises(TypeError):
        iso532.loudness_zwtv(sig.astype(np.float32), FS)
    with pytest.raises(TypeError):
        iso532.loudness_zwtv(sig[::2], FS)
