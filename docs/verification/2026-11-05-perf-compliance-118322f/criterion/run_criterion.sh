#!/bin/sh
# Interleaved Criterion A/B: v0.3.1 vs v0.4.0, 3 rounds, default threads and RAYON_NUM_THREADS=1.
set -e
OUT=<REPO>/tmp/perf-2026-11-05
for r in 1 2 3; do
  for v in 0.3.1 0.4.0; do
    EXE=$(ls <REPO>/tmp/target-bench-v$v/release/deps/loudness-*.exe | head -1)
    CARGO_TARGET_DIR=<REPO>/tmp/target-bench-v$v "$EXE" --bench --noplot > "$OUT/criterion-v$v-t12-r$r.log" 2>&1
    CARGO_TARGET_DIR=<REPO>/tmp/target-bench-v$v RAYON_NUM_THREADS=1 "$EXE" --bench --noplot "zwtv_10s|stream_push_10s_480chunk" > "$OUT/criterion-v$v-t1-r$r.log" 2>&1
    echo "done v$v round $r $(date +%H:%M:%S)"
  done
done
