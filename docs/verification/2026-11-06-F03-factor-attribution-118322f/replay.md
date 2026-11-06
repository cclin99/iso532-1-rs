# Replay

All paths relative to the repository root; the working folder of this round was `tmp/factor-2026-11-06/` (gitignored). Inputs are the frozen 2026-11-05 inputs `tmp/impl-2026-11-05/in/sig{1..25}.f64` (int16/32768 × 2√2 Pa, little-endian binary64; SHA-256 in `results.json["input_hashes"]`) and `sig1-levels.f64`.

1. **Rust stage dumps** (iso532 at `62e8559`, crate identical to `118322f`; shipped tables):
   `cargo build --release` in `harness/` (Cargo.toml / main.rs delivered as `.txt`), then
   `stage-dump <in> out/rust s22 1.0` and `stage-dump <in> out/rust cal 1.002605897666858` (factor from `calibration.json`).
2. **Port validation**: `python validate.py > logs/validate.log` (needs the 2026-11-05 SQAT outputs `tmp/impl-2026-11-05/out/sqat_0.24-*`).
3. **Factorial**: `python run_factorial.py 6` → `out/fact/*.npy` (32 cells + negative control per signal), `logs/factorial.log`.
4. **SQAT with the ZUP constant removed** (GNU Octave 11.3.0; SQAT v2.0 tree at `tmp/sqat-claude-2026-11-06/sqat-v2.0`, tag `94f489c`; variant folders contain only the patched `Loudness_ISO532_1.m`, see the two diffs):
   `octave-cli --no-gui --eval "addpath('<here>/sqat'); run_sqat_variant('<sqat_root>','<here>/sqat/var-e0-024','sqat_e0_0.24','<in>','<here>/out/sqat',1:25)"` and the same with `var-e0-022` / `sqat_e0_0.22`. ≈ 70 min per variant.
5. **Analysis**: `python analyze.py results.json` (reads the workbooks under `tmp/c01-material/official/`, the official CLI outputs of the 2026-11-05 round under `tmp/usl-2026-11-05/cli-v0{22,24}/sig*/`, the 2026-11-05 SQAT / MoSQITo / iso532 outputs and everything above).
6. **Delivery**: `python finalize_delivery.py docs/verification/2026-11-06-F03-factor-attribution-118322f`.
