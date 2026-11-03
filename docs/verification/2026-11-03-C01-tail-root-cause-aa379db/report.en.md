# C-01 total-tail root-cause investigation

2026-11-03 (Asia/Taipei), independent verifier Astra. Snapshot `aa379db8f3dc37f5048ac6c8b7a6d4ba2a6c3b76`. [繁體中文](report.md) · [preregistered design](experiment-design.en.md).

## 1. Conclusion

**The dominant confirmed cause is Rust's intermediate per-frame total-loudness rounding, followed by other slope semantics; this is not an extra-tail indexing failure.** Holding the nonlinear history and temporal weighting fixed, removing only the rounding explains 67.2893%–98.3967% of the four original signed differences. It does **not** meet the unchanged 1e-14 sone gate for any signal. The full stage decomposition is quantitatively closed, but the remaining slope differences have not all been traced to a single branch/constant. C-01 acceptance remains open; no production fix or normative coefficient decision is made.

| Signal | Baseline R−C (sone) | Rounding contribution % | Residual after removing rounding | Residual after raw cell22 |
|---|---|---|---|---|
| 18 | -2.156775583e-07 | 93.97182728 | -1.300141574e-08 | 1.225633281e-09 |
| 23 | -4.170520259e-07 | 67.28927507 | -1.36420741e-07 | -8.452009531e-09 |
| 24 | -2.99306343e-07 | 97.27845763 | -8.145748935e-09 | 6.027779456e-10 |
| 25 | -2.028349099e-07 | 98.39667769 | -3.252097354e-09 | -3.252097354e-09 |


Rust `calc_slopes.rs:161-165` rounds every 2 kHz total to 0.001 sone below/equal 16, or 0.01 above 16; official C `f_calc_slopes` has no corresponding rounding. Re-rounding the raw Rust history reproduces its original rounded history **bitwise**. The resulting historical differences pass through TW; rounding just the final displayed number is not what the implementation does. The tiny final unweighted spectrum can agree while weighted total still carries prior differences.

## 2. Evidence validity and ordered attribution

New calculations use the same hashed pressure bytes, fresh fixed-commit snapshot, unchanged official C SHA-256 `a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491`, MSVC 19.44.35228 `/O2 /fp:precise`, Rust 1.99.1 release/default dispatch. Both old public tail baselines reproduce **bitwise** for all four signals. C replay matches public total/specific at every internal frame; Rust replay matches all public sampled total/specific values bitwise. Full internal arrays cover filter/SPL, corrected main, nonlinear, slope total/specific and TW. Same-input stage comparisons include both upstream directions; complete first chronological differences, maxima and coordinates are in JSON/CSV.

The first wrapper attempt correctly failed its input-immutability guard because official C main loudness mutates its SPL argument. `attempt-1-*` preserves the evidence. The wrapper now supplies a private copy, then calls the original routines; the complete experiment reran in fresh `run2`. A preceding Python syntax error is also recorded. No failed attempt is promoted to a pass. Preregistered design hashes are unchanged.

Define E_i=T_i−T_C; each contribution is E_(i−1)−E_i, keeping Rust TW until the final step. The fixed order was rounding → slopes → nonlinear → main → filter → TW. These signed contributions are order-dependent, not unique independent percentages; cancellations are retained. Maximum telescoping reconstruction error is **0 sone**. Replacing main and all downstream stages leaves at most 5.095750210681871e-18 sone; final all-C substitution is exact.

| Signed contribution (sone) | 18 | 23 | 24 | 25 |
|---|---|---|---|---|
| remove_R_rounding | -2.026761426e-07 | -2.806312849e-07 | -2.911605941e-07 | -1.995828125e-07 |
| replace_slopes_C | -1.296987679e-08 | -1.363086719e-07 | -8.110269432e-09 | -3.212727779e-09 |
| replace_NL_C | 0 | 1.301042607e-18 | 0 | 0 |
| replace_main_C | -3.153894962e-11 | -1.120690893e-10 | -3.54795002e-11 | -3.936957466e-11 |
| replace_filter_C | 5.095750211e-18 | 0 | -3.252606517e-18 | 0 |
| replace_TW_C | 0 | -2.168404345e-18 | 0 | -6.505213035e-19 |


Comparator self/finite/shape/known-coordinate perturbation controls and TW propagation controls pass for all four signals. On identical C/Rust rounded/raw histories, the largest target difference between TW implementations is **4.33680869e-18 sone**. TW arithmetic therefore does not explain the observed 1e-7 scale discrepancy; it transports the different upstream histories. The original strict baseline gate remains failed. Broad workspace/binding/package tests were intentionally skipped; no input/build blocker remains.

## 3. Concrete slope and main controls

**USL cell:** changing only raw Rust `USL[12][4]` from 0.24 to 0.22 has a causal numerical effect for signals 18/23/24, but **zero effect for 25**. Thus this single cell cannot explain all four cases. This is a same-history counterfactual against the archived C, not evidence deciding which standard edition's cell is authoritative.

| Signal | 0.22−0.24 effect (sone) | Other same-input slope gap: raw22−C | Gap after C epsilon=0 + tables64 |
|---|---|---|---|
| 18 | 1.422704902e-08 | 1.257172226e-09 | 1.291724238e-09 |
| 23 | 1.279687315e-07 | -8.339940441e-09 | -8.400504273e-09 |
| 24 | 8.748526881e-09 | 6.382574491e-10 | 6.926491861e-10 |
| 25 | 0 | -3.212727779e-09 | -3.178040338e-09 |


C slope epsilon removal alone and cumulative binary64 ZUP/RNS/USL tables do not remove the main residual. The final column fixes the same Rust nonlinear history and Rust TW. Those variants leave Bark row 239 unwritten in every frame: respectively 4340, 5108, 4808 and 5108 nonfinite sentinel values per variant. Only finite TOTAL is used; they are **not** valid specific-output replacements. The 0.1f grid was deliberately unchanged. This deviation is retained, not masked.

**Main coefficient:** C `.0635f` is binary32-rounded before promotion; Rust `0.0635` is binary64. Changing only that literal in a diagnostic C copy explains **96.9374%–99.5930% of the already much smaller main-stage gap**. The cumulative 0.4f/0.32f correction control adds little. These percentages refer to the main-stage gap, not the whole original error. Unisolated main residuals remain above 1e-14.

| Signal | Original main-stage gap | MP1-only fraction % | Remaining after MP1 only | Remaining after MP1 + correction |
|---|---|---|---|---|
| 18 | -3.153894962e-11 | 97.85438801 | -6.767034849e-13 | -6.760548068e-13 |
| 23 | -1.120690893e-10 | 99.59296241 | -4.561633189e-13 | -4.561633189e-13 |
| 24 | -3.54795002e-11 | 96.93742981 | -1.086584598e-12 | -1.084293896e-12 |
| 25 | -3.936957466e-11 | 97.88150114 | -8.340439884e-13 | -8.340439884e-13 |


**r8 comparison rounding:** the final bounded 2×2 control changes only r8 to identity in raw cell24/cell22 variants. It greatly worsens agreement rather than resolving the small residual and shows interaction with the cell. It rejects a naive r8-removal fix; its large intervention effect is not an attribution of the original small residual.

| Signal | r8 off/cell22 residual vs same-input original C | Cell × r8 interaction |
|---|---|---|
| 18 | -0.0001379427263 | 5.540427184e-07 |
| 23 | -0.0005117469018 | -6.705230238e-06 |
| 24 | -0.0001547866186 | -1.400052247e-08 |
| 25 | -0.0001172302946 | 0 |


## 4. Confirmed, inferred and unresolved

- **Confirmed:** intermediate total rounding dominates; the coefficient cell matters in three signals but not the fourth; main `.0635f` precision explains most of the main-stage contribution. The full ordered stage contributions reconstruct all four original differences. Baseline/replay/finite/control gates pass; rounding removal alone fails the strict target.
- **Supported interpretation:** historical upstream differences, rather than padded-input alignment, drive the weighted tails. Filter/nonlinear/TW substitutions contribute only approximately 1e-18 sone at these four tails under the declared order.
- **Unresolved:** after cell22, epsilon/table controls, same-input raw-slope differences remain **6.926491860539258e-10 to 8.400504272667447e-9 sone in absolute value**. The detailed segmentation/comparison mechanism is not isolated. After the cumulative main literals, residuals remain **4.561633189237302e-13 to 1.0842938959892967e-12 sone**; table precision/arithmetic/branch effects were not individually resolved. Removing r8 is demonstrably not a valid shortcut. No combination was claimed as a production correction, and no remaining error was relabelled as acceptable merely because it is small.

All detailed controls were bounded and explicitly marked exploratory in dated addenda, without revising the original threshold or design. The next implementation decision needs a separate design/review; this report does not authorize edits or close C-01.

## 5. Delivery and reproduction

- [results.json](results.json), [tail-decomposition.csv](tail-decomposition.csv), [stage-coordinates.csv](stage-coordinates.csv): complete primary metrics, signed effects, decimal17/binary64 evidence.
- [main-literal-controls.json](main-literal-controls.json), [slopes-controls.json](slopes-controls.json), [r8-control.json](r8-control.json): bounded exploratory controls and remaining gaps.
- [commands.md](commands.md), [run_experiment.py](run_experiment.py), [run-log.json](run-log.json): reproduction, exact build/execution commands, versions and exit codes. Supplement scripts/logs and all transformation diffs are adjacent.
- [source-input-hashes.json](source-input-hashes.json), [delivery-check.md](delivery-check.md), [delivery-integrity.json](delivery-integrity.json): original-material provenance and final redacted-delivery integrity.

Only UTF-8 text is delivered. WAV/binaries/full raw stage arrays stay in scratch with hashes; native source was not edited. Original source/input/binary/harness hashes retain their meanings; the final manifest hashes post-redaction delivery bytes and excludes itself. Existing C-01/F-03 rounds, DSP/tests/goldens/decision/audit row are unchanged; no commit/push. The main agent maintains the index separately.
