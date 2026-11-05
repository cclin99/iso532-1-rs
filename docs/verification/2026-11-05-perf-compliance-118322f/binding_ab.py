"""Rust-binding timing only (no MoSQITo): the compare_mosqito.py signal and loop, one wheel per process."""
import statistics, sys, time, pathlib, json
sys.path.insert(0, str(pathlib.Path(sys.argv[1]) / "tools"))
from iso532_testkit import contract_signal
import iso532, importlib.metadata as md
x = contract_signal(144000)
iso532.loudness_zwtv(x, 48000.0)
d = []
for _ in range(30):
    t0 = time.perf_counter(); iso532.loudness_zwtv(x, 48000.0); d.append(time.perf_counter() - t0)
print(json.dumps({"wheel": md.version("iso532"), "mean_ms": statistics.mean(d) * 1e3,
                  "sd_ms": statistics.stdev(d) * 1e3, "median_ms": statistics.median(d) * 1e3, "min_ms": min(d) * 1e3}))
