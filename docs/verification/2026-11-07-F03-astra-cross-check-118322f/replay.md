# Replay

Working folder (not tracked): `tmp/compare-2026-11-07/`, next to the factor-attribution working folder `tmp/factor-2026-11-06/`. Its cell outputs `out/fact/*.npy` and `results.json` are required; their SHA-256 are in that round's `raw-output-hashes.json`.

1. Build the levels-to-core harness against the product crate (`iso532/` at `118322f`; this round used HEAD `8b42f93`, crate identical). Sources: `levels2core.Cargo.toml.txt`, `levels2core.main.rs.txt`, lock file `levels2core.Cargo.lock.txt`.

   ```
   cd levels2core && cargo build --release
   ```

2. Reproduce Astra's 2026-11-05 downstream residual and attribute it. Reads Astra's `frontend-results.jsonl.txt` and `c-fullprecision-controls.json`; writes `astra_residual.json`; log `run-astra_residual.log`.

   ```
   python astra_residual.py
   ```

3. Cross-check against the three Astra rounds. Reads Astra's `all-tv-cancellation.json` and `tv-paired-effects.json`, the Claude round's `results.json` and cells, and the workbooks; writes `crosscheck.json`; log `run-crosscheck.log`.

   ```
   python crosscheck.py
   ```

4. Recompute the USL main effect with Astra's definition (mean over calibrations). Writes `usl_main_effect_definition.json`; log `run-usl_main_effect_definition.log`.

   ```
   python usl_main_effect_definition.py
   ```

Python 3.11.9 with numpy and openpyxl. The workbook loader prints an openpyxl conditional-formatting warning that does not affect the values read.
