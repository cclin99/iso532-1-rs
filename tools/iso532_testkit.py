"""Shared helpers for the cross-language bitwise contract (single source)."""

import numpy as np

KNOWN_ANSWER = 0xB90557CFD5E83390


def contract_signal(n=48000):
    """純整數演算訊號(無 libm,Python/Rust 逐位相同)。"""
    i = np.arange(n, dtype=np.uint64)
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


if fnv1a_f64(np.array([0.0, 1.0, 2.0, 3.0])) != KNOWN_ANSWER:
    raise RuntimeError("fnv1a_f64 port drifted from the Rust reference")
