# Exploratory main-loudness literal controls

Time / 時間: 2026-11-03T13:05:30.974700+00:00
Primary results SHA-256 (before redaction): c8e8915c6902c8896c40ae1c728e311563ba59089bdf1cbb3c9331605f228d31

Written after the preregistered six-step experiment and before these extra runs. This is explicitly exploratory; the original design and 1e-14 gate remain unchanged. The primary decomposition localized an additional 3.15e-11 to 1.12e-10 sone to the main-loudness implementation at the target.

Hypothesis: official C `.0635f` (binary32 rounded then promoted to binary64) versus Rust `0.0635` (binary64) explains part or all of that stage contribution. A second cumulative variant also changes only `0.4f` and `0.32f` in the low-band correction to double literals. Preserve every other table, constant, branch and arithmetic operation. Generate two diagnostic C source copies in new scratch, complete diffs and hashes; original C remains unmodified. Use the corrected wrapper with private SPL work copy.

For each of four signals, use the identical frozen Rust SPL history already measured. Run each variant main stage, then ORIGINAL C nonlinear/slopes and ORIGINAL Rust TW. Compare the variant tail to original C-main and Rust-main paths with the same upstream/downstream. Report signed literal effect, fraction of the original main-stage gap, remaining gap and whether it meets 1e-14. Record full core-history metrics and array/binary hashes. Remaining table precision/order/branch effects are unresolved unless separately tested. These interventions do not authorize a production change or normative judgment.
