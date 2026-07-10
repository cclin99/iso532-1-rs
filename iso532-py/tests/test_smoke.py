"""Smoke + cross-language bitwise contract tests (no mosqito; runs in CI)."""
import numpy as np
import pytest

import iso532

FS = 48000.0

# Frozen from Rust (R3-P2 tooling):
#   cd iso532-ffi && cargo test --test ffi dump_py_bitwise_contract_hashes -- --ignored --nocapture
# n/time_axis are bitwise-stable across platforms and backends (see
# docs/CI-HASH-GATE-DEBUG-2026-07-10.md). Values MUST come from an actual
# dump run — never invented, never copied from another signal.
N_HASH = 0x0     # 凍結步驟(Task 3)以實測值取代
TIME_HASH = 0x0  # 凍結步驟(Task 3)以實測值取代


def py_contract_signal():
    """純整數演算訊號:與 iso532-ffi/tests/ffi.rs 的 py_contract_signal 逐位相同。"""
    i = np.arange(48000, dtype=np.uint64)
    return ((i * np.uint64(2654435761)) % np.uint64(96001)).astype(
        np.float64
    ) / 96000.0 * 0.02 - 0.01


def fnv1a_f64(arr):
    """與 iso532/tests/common/mod.rs 的 fnv1a_f64 同一演算法。"""
    h = 0xCBF29CE484222325
    for b in np.ascontiguousarray(arr, dtype="<f8").tobytes():
        h ^= b
        h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return h


def test_zwtv_shapes_and_axes():
    n, spec, bark, time = iso532.loudness_zwtv(py_contract_signal(), FS)
    assert n.shape == (500,)
    assert time.shape == (500,)
    assert spec.shape == (240, 500)
    assert bark.shape == (240,)
    assert bark[0] == pytest.approx(0.1)
    assert bark[-1] == pytest.approx(24.0)
    assert np.all(np.isfinite(n)) and np.all(n >= 0)


def test_zwtv_diffuse_accepted():
    n, _spec, _bark, _time = iso532.loudness_zwtv(py_contract_signal(), FS, "diffuse")
    assert n.shape == (500,)


def test_zwst_shapes():
    n, spec, bark = iso532.loudness_zwst(py_contract_signal(), FS)
    assert isinstance(n, float) and n > 0
    assert spec.shape == (240,)
    assert bark.shape == (240,)


def test_bitwise_contract_n_and_time_axis():
    n, _spec, _bark, time = iso532.loudness_zwtv(py_contract_signal(), FS)
    assert hex(fnv1a_f64(n)) == hex(N_HASH)
    assert hex(fnv1a_f64(time)) == hex(TIME_HASH)


def test_error_mapping():
    sig = py_contract_signal()
    with pytest.raises(ValueError, match="48000"):
        iso532.loudness_zwtv(sig, 44100.0)
    with pytest.raises(ValueError, match="too short"):
        iso532.loudness_zwtv(sig[:100].copy(), FS)
    with pytest.raises(ValueError, match="field_type"):
        iso532.loudness_zwtv(sig, FS, "FREE")


def test_strict_input_contract():
    sig = py_contract_signal()
    with pytest.raises(TypeError):
        iso532.loudness_zwtv(sig.astype(np.float32), FS)
    with pytest.raises(TypeError):
        iso532.loudness_zwtv(sig[::2], FS)
