"""Reproduce the README's 3-second ISO532/MoSQITo comparison."""

import argparse
import platform
import statistics
import sys
import time
from pathlib import Path

import numpy as np
from mosqito.sq_metrics import loudness_zwtv as mosqito_loudness_zwtv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from iso532_testkit import contract_signal  # noqa: E402

import iso532  # noqa: E402

FS = 48_000


def measured_runs(function, signal, iterations):
    function(signal, float(FS))
    durations = []
    result = None
    for _ in range(iterations):
        start = time.perf_counter()
        result = function(signal, float(FS))
        durations.append(time.perf_counter() - start)
    return durations, result


def print_timing(label, durations, duration_s):
    mean_s = statistics.mean(durations)
    stdev_s = statistics.stdev(durations) if len(durations) > 1 else 0.0
    print(
        f"{label}: mean={mean_s:.6f} s, sample_sd={stdev_s:.6f} s, "
        f"min={min(durations):.6f} s, max={max(durations):.6f} s, "
        f"real_time={duration_s / mean_s:.4f}x"
    )
    return mean_s


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=30)
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("--iterations must be at least 1")

    duration_s = 3
    signal = np.ascontiguousarray(contract_signal(duration_s * FS), dtype=np.float64)
    rust_runs, rust = measured_runs(iso532.loudness_zwtv, signal, args.iterations)
    mosqito_runs, reference = measured_runs(
        mosqito_loudness_zwtv, signal, args.iterations
    )

    rust_n, rust_specific = rust[:2]
    reference_n, reference_specific = reference[:2]
    max_n = float(np.max(np.abs(rust_n - np.asarray(reference_n))))
    max_specific = float(
        np.max(np.abs(rust_specific - np.asarray(reference_specific)))
    )

    print(f"platform: {platform.platform()}")
    print(f"python: {platform.python_version()}; numpy: {np.__version__}")
    print(f"signal: contract_signal({duration_s * FS}), float64 contiguous, {FS} Hz")
    print(f"iterations per implementation: {args.iterations} (after one warm-up)")
    rust_s = print_timing("ISO532 Rust binding", rust_runs, duration_s)
    mosqito_s = print_timing("MoSQITo", mosqito_runs, duration_s)
    print(f"relative speed from arithmetic means: {mosqito_s / rust_s:.2f}x")
    print(f"max abs N(t) difference: {max_n:.6e} sone")
    print(
        "max abs N_specific(t) difference: "
        f"{max_specific:.6e} sone/Bark"
    )


if __name__ == "__main__":
    main()
