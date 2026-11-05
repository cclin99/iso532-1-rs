"""Summarise interleaved Criterion logs: point estimate per round, median of rounds, 0.4.0 vs 0.3.1."""
import json, re, pathlib, statistics
here = pathlib.Path(__file__).parent
unit = {"ns": 1e-6, "µs": 1e-3, "us": 1e-3, "ms": 1.0, "s": 1e3}
data = {}
for log in sorted(here.glob("criterion-v*-t*-r*.log")):
    v, t, r = re.match(r"criterion-v([\d.]+)-(t\d+)-r(\d)\.log", log.name).groups()
    name = None
    for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^(\S+/\S+)", line)
        if m:
            name = m.group(1)
        m = re.search(r"time:\s+\[([\d.]+) (\S+) ([\d.]+) (\S+) ([\d.]+) (\S+)\]", line)
        if m and name:
            est = float(m.group(3)) * unit[m.group(4)]
            key = re.sub(r"_t\d+", "", name).replace("/480000", "")
            data.setdefault(f"{t}:{key}", {}).setdefault(v, []).append(est)
            name = None
rows = []
for k, d in sorted(data.items()):
    a, b = statistics.median(d["0.3.1"]), statistics.median(d["0.4.0"])
    rows.append({"bench": k, "v0.3.1_ms": d["0.3.1"], "v0.4.0_ms": d["0.4.0"],
                 "median_0.3.1_ms": a, "median_0.4.0_ms": b, "change_pct": (b / a - 1) * 100,
                 "per_output_frame_us_0.4.0": b * 1000 / 5000})
(here / "criterion-summary.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
for r in rows:
    print(f"{r['bench']:42s} 0.3.1 {r['median_0.3.1_ms']:9.3f}  0.4.0 {r['median_0.4.0_ms']:9.3f}  {r['change_pct']:+6.1f}%   rounds031={['%.1f'%x for x in r['v0.3.1_ms']]} rounds040={['%.1f'%x for x in r['v0.4.0_ms']]}")
