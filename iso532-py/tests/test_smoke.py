"""Smoke + cross-language bitwise contract tests (no mosqito; runs in CI)."""
import os
import sys

import numpy as np
import pytest

from iso532_testkit import contract_signal, fnv1a_f64  # noqa: E402

import iso532  # noqa: E402

FS = 48000.0

# Frozen from Rust:
#   cd iso532 && cargo test --test py_contract_dump -- --ignored --nocapture
# Values MUST come from an actual dump run — never invented, never copied from
# another signal.
# F-02 (2026-10-31): the default nonlinear-decay initialisation moved from the
# MoSQITo tail seed to zero state. The tail-seed hash is kept for
# nl_init="mosqito_tail".
# 0.4.0 (2026-11-04, F-04): the total loudness is no longer rounded to 0.001
# sone per frame. That rounding is what made n bitwise-stable across platforms;
# n now carries the same libm ULP noise as n_specific (see iso532/tests/
# hash_gate.rs), so the N hashes are per OS like the Rust hash gate: linux from
# an ubuntu:24.04 container (glibc 2.39, matches GitHub runners), windows from
# the machine that froze them (UCRT varies by CPU/OS build; HASH_GATE_DUMP_ONLY=1
# turns the N-hash comparison into a dump, as for the Rust hash gate).
# time_axis is unchanged and still bitwise-stable everywhere.
N_HASHES = {
    # platform: (N_HASH, N_HASH_MOSQITO_TAIL), AVX2 runtime dispatch
    "linux": (0x046FDC830A43E1E2, 0x2CD05C64E0CB8931),
    "win32": (0xFF2754E949A15287, 0xAA3D499447B9A2C4),
}
TIME_HASH = 0xF076BCB342595537


def check_n_hash(n, which):
    got = fnv1a_f64(n)
    frozen = N_HASHES.get(sys.platform)
    if frozen is None or os.environ.get("HASH_GATE_DUMP_ONLY") == "1":
        print(f"py-contract {which}: n={got:#018x} (dump-only on {sys.platform})")
        return
    want = frozen[0 if which == "zero" else 1]
    assert hex(got) == hex(want), f"{which} N hash drifted on {sys.platform}"


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
    check_n_hash(n, "zero")
    assert hex(fnv1a_f64(time)) == hex(TIME_HASH)


def test_bitwise_contract_mosqito_tail_init():
    n, _spec, _bark, time = iso532.loudness_zwtv(
        contract_signal(), FS, nl_init="mosqito_tail"
    )
    check_n_hash(n, "mosqito_tail")
    assert hex(fnv1a_f64(time)) == hex(TIME_HASH)
    n_zero, *_ = iso532.loudness_zwtv(contract_signal(), FS, nl_init="zero")
    check_n_hash(n_zero, "zero")
    # the two initialisations differ at the start and converge later
    assert n_zero[0] == 0.0 and n[0] > 0.0
    assert abs(n_zero[-1] - n[-1]) < 1e-9


def test_nl_init_rejects_unknown_value():
    import pytest

    with pytest.raises(ValueError, match="nl_init"):
        iso532.loudness_zwtv(contract_signal(), FS, nl_init="last_frame")


def test_error_mapping():
    sig = contract_signal()
    with pytest.raises(ValueError, match="48000"):
        iso532.loudness_zwtv(sig, 44100.0)
    with pytest.raises(ValueError, match="too short"):
        iso532.loudness_zwtv(sig[:100].copy(), FS)
    with pytest.raises(ValueError, match="field_type"):
        iso532.loudness_zwtv(sig, FS, "FREE")


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("idx", [0, 24_000, 47_999])
def test_batch_rejects_nonfinite_input(value, idx):
    # C-02: batch functions reject NaN/Inf (core error code 4 -> ValueError);
    # the stream path keeps flagging instead (see test_stream.py).
    sig = contract_signal()
    sig[idx] = value
    with pytest.raises(ValueError, match=f"non-finite sample.*index {idx}"):
        iso532.loudness_zwtv(sig, FS)
    with pytest.raises(ValueError, match=f"non-finite sample.*index {idx}"):
        iso532.loudness_zwst(sig, FS)


@pytest.mark.parametrize(
    "length", [4800, 4801, 4823, 4824, 4825, 4895, 4896, 4897, 47905, 47927, 47928, 47999, 48000]
)
def test_zwtv_output_grid_contract(length):
    # C-01: frames = ceil(ceil(L/24)/4); time[j] = 96 j / 48000 exactly; prefix-determined.
    sig = contract_signal()[:length].copy()
    n, spec, _bark, time = iso532.loudness_zwtv(sig, FS)
    frames = -(-(-(-length // 24)) // 4)
    assert n.shape == (frames,)
    assert time.shape == (frames,)
    assert spec.shape == (240, frames)
    assert np.array_equal(time, np.arange(frames) * 96 / 48000.0)
    full_n, full_spec, _b, _t = iso532.loudness_zwtv(contract_signal(), FS)
    assert np.array_equal(n, full_n[:frames])
    assert np.array_equal(spec, full_spec[:, :frames])


def test_strict_input_contract():
    sig = contract_signal()
    with pytest.raises(TypeError):
        iso532.loudness_zwtv(sig.astype(np.float32), FS)
    with pytest.raises(TypeError):
        iso532.loudness_zwtv(sig[::2], FS)


def test_sone2phon_matches_frozen_formula():
    n = np.arange(0.0, 20.0001, 0.02)
    expected = np.empty_like(n)
    high = n >= 1.0
    expected[high] = 40.0 + 10.0 * np.log2(n[high])
    expected[~high] = 40.0 * np.power(n[~high] + 0.0005, 0.35)
    got = np.array([iso532.sone2phon(float(value)) for value in n])
    np.testing.assert_allclose(got, expected, rtol=0.0, atol=1e-12)
    assert iso532.sone2phon(1.0) == pytest.approx(40.0, abs=1e-12)
    assert iso532.sone2phon(2.0) == pytest.approx(50.0, abs=1e-12)
    assert iso532.sone2phon(4.0) == pytest.approx(60.0, abs=1e-12)


def test_sone2phon_rejects_negative_sone():
    with pytest.raises(ValueError, match="sone must be non-negative"):
        iso532.sone2phon(-0.001)


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_sone2phon_rejects_nonfinite_sone(value):
    with pytest.raises(ValueError, match="sone must be non-negative"):
        iso532.sone2phon(value)
