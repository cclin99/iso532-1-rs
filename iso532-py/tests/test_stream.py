"""Streaming API (ZwtvStream) tests — no mosqito; runs in CI.

NaN semantics deliberately differ from the batch API: streaming zeroes
non-finite samples and raises flags instead of raising exceptions.
"""
import numpy as np
import pytest

import iso532

FS = 48000.0
CHUNK = 480


def py_contract_signal():
    """Pure integer signal, matching test_smoke.py (never synthesize with sin)."""
    i = np.arange(48000, dtype=np.uint64)
    return ((i * np.uint64(2654435761)) % np.uint64(96001)).astype(
        np.float64
    ) / 96000.0 * 0.02 - 0.01


def run_chunked(sig, chunk):
    s = iso532.ZwtvStream("free")
    parts = [
        s.push(sig[start : start + chunk]) for start in range(0, len(sig), chunk)
    ]
    parts.append(s.flush())
    return tuple(np.concatenate([p[k] for p in parts]) for k in range(4))


def test_constants_are_frozen():
    assert iso532.ZwtvStream.latency_samples() == 24
    assert iso532.N_WARMUP_FRAMES == 580
    assert iso532.FLAG_CLAMPED_120DB == 1
    assert iso532.FLAG_NONFINITE_INPUT == 2
    assert iso532.FLAG_WARMUP == 4


def test_max_frames_for_chunk_bounds_push_output():
    sig = py_contract_signal()
    for chunk in (1, 24, CHUNK, 4096):
        cap = iso532.ZwtvStream.max_frames_for_chunk(chunk)
        s = iso532.ZwtvStream()
        for start in range(0, len(sig), chunk):
            n, _, _, _ = s.push(sig[start : start + chunk])
            assert len(n) <= cap


def test_chunk_invariance_bitwise():
    sig = py_contract_signal()
    base = run_chunked(sig, len(sig))
    for chunk in (1, 24, CHUNK, 4096):
        got = run_chunked(sig, chunk)
        for label, g, b in zip(("n", "n_phon", "t", "flags"), got, base):
            assert g.tobytes() == b.tobytes(), f"chunk={chunk}/{label}"


def test_stream_matches_batch_after_warmup():
    sig = py_contract_signal()
    batch_n, _, _, _ = iso532.loudness_zwtv(sig, FS)
    n, n_phon, t_idx, flags = run_chunked(sig, CHUNK)
    assert len(n) == len(batch_n)  # 500
    assert np.array_equal(t_idx, np.arange(len(n), dtype=np.uint64))
    w = iso532.N_WARMUP_FRAMES
    assert np.max(np.abs(n[w:] - batch_n[w:])) <= 1e-9
    assert np.array_equal((flags & iso532.FLAG_WARMUP) != 0, t_idx < w)
    for v, s in zip(n[w : w + 8], n_phon[w : w + 8]):
        assert s == iso532.sone2phon(float(v))


def test_nan_is_flagged_not_raised():
    sig = py_contract_signal().copy()
    sig[4800:4848] = np.nan
    n, _, _, flags = run_chunked(sig, CHUNK)
    assert np.any((flags & iso532.FLAG_NONFINITE_INPUT) != 0)
    assert np.all(np.isfinite(n))


def test_tail_nan_surfaces_in_residual_flags():
    sig = np.zeros(48_048)
    sig[48_030] = np.nan
    s = iso532.ZwtvStream()
    n, _, _, flags = s.push(sig)
    assert len(n) == 501
    assert not np.any((flags & iso532.FLAG_NONFINITE_INPUT) != 0)
    fn, _, _, _ = s.flush()
    assert len(fn) == 0
    assert s.residual_flags & iso532.FLAG_NONFINITE_INPUT


def test_push_after_flush_raises_and_reset_recovers():
    sig = py_contract_signal()
    s = iso532.ZwtvStream()
    s.push(sig[:CHUNK])
    s.flush()
    fn, _, _, _ = s.flush()  # Idempotent: no raise, empty output.
    assert len(fn) == 0
    with pytest.raises(RuntimeError, match="reset"):
        s.push(sig[:CHUNK])
    s.reset()
    dirty_then_reset = [
        s.push(sig[start : start + CHUNK]) for start in range(0, len(sig), CHUNK)
    ]
    dirty_then_reset.append(s.flush())
    got = tuple(np.concatenate([p[k] for p in dirty_then_reset]) for k in range(4))
    base = run_chunked(sig, CHUNK)
    for label, g, b in zip(("n", "n_phon", "t", "flags"), got, base):
        assert g.tobytes() == b.tobytes(), f"reset/{label}"


def test_input_validation():
    sig = py_contract_signal()
    s = iso532.ZwtvStream()
    with pytest.raises(TypeError):
        s.push(sig.astype(np.float32))
    with pytest.raises(TypeError):
        s.push(sig[::2])
    with pytest.raises(ValueError, match="field_type"):
        iso532.ZwtvStream("FREE")
