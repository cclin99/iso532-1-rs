# Exploratory slope boundary and literal controls

Timestamp: 2026-11-03T13:08:05.503571+00:00

Written after the primary experiment and before these controls. Fix the already recorded Rust nonlinear history and Rust TW. Compare raw Rust cell22 with original C slopes on that same history. Two generated C-only diagnostic copies: (A) change only `_ZUP += .0001f` to zero; (B) additionally remove f suffixes from ZUP/RNS/USL table literals. Preserve the C slope algorithm, USL cell value 0.22, and 0.1f specific-grid accumulation. Full diffs/hashes are required; original C is unchanged. This is exploratory, not a changed preregistered acceptance criterion or normative choice.

Report target total effect/residual and full total-history difference. These controls concern TOTAL ONLY: removing the epsilon may change specific-grid coverage. Initialize specific buffers to NaN, record unwritten/nonfinite counts and first coordinates, and do not claim specific equivalence. Do not silently normalize the grid or replace NaNs to make a full-pipeline pass. Remaining gaps after the two controls are unresolved slope-implementation effects unless independently isolated. Stop after these small controls and finalize the report; 1e-14 remains unchanged.
