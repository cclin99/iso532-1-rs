# F-03 cross-check: the Claude factor-attribution round against the three Astra rounds

> [繁體中文](report.md) · Claude Opus 5.5 (main agent, not Astra) · 2026-11-07 Asia/Taipei

Deliveries compared:

- Claude: [`2026-11-06-F03-factor-attribution-118322f/`](../2026-11-06-F03-factor-attribution-118322f/) (commit `8b42f93`). That round was finished before Astra delivered and did not consult Astra's results.
- Astra: [`2026-11-05-F03-filter-independent-118322f/`](../2026-11-05-F03-filter-independent-118322f/), [`2026-11-06-F03-three-implementations-118322f/`](../2026-11-06-F03-three-implementations-118322f/), [`2026-11-06-F03-factorial-matrix-118322f/`](../2026-11-06-F03-factorial-matrix-118322f/).

Product snapshot `118322f` (v0.4.0). This round builds at repository HEAD `8b42f93`; `iso532/` is identical to `118322f`. Only Astra's delivered machine-readable files were read. No Astra file, product code or golden data was changed.

## 1. Conclusions

1. **The numbers agree.** Wherever both sides computed the same quantity, Astra and Claude agree within 1e-8, and the MoSQITo maxima agree to every digit. The two sides used different Octave versions, harnesses and alignment code.
2. **The "downstream residual not traced" in Astra's 2026-11-05 round is the ZUP band-edge constant `+0.0001`.** That residual is the difference between the iso532 slope stage and the official C program on identical 28-band levels: up to 1.5e-4 in N′ and 1.59e-5 in N. With the constant added to the slope port, the N′ difference drops to ≤ 1.7e-7 and the N difference to ≤ 6.6e-7. On signal 5 the N difference is exactly 1e-4 × the band-0 core loudness.
3. **The "error cancellation" in Astra's matrix report exists only in MoSQITo.** On the official C, SQAT and iso532 path, the largest "improvement" of 0.24 over 0.22 is 5.75e-5 and no point improves by more than 1e-4. That is within the 4-decimal quantization of the workbooks. 12,730 points get worse by more than 1e-4. MoSQITo has its own residual of about 0.023 sone (F-04…F-07 and rounding), and only there does 0.24 partly cancel at individual points.
4. **The rounds complement each other and do not conflict.** Astra has controls Claude did not run: float32 input quantization, MoSQITo rounding, filter history and skip, and the 47 equidistant points correction. Claude has factors Astra's matrix did not include: the ZUP constant and iso532 itself.
5. **The open 0.5.0 decisions are unchanged.** All three remain with the user: `USL[12][4]` = 0.22, the Annex A front end for ZWST, and whether calc_slopes adopts the ZUP constant. Astra's evidence argues against none of them.

## 2. Numerical agreement

| Quantity | Astra | Claude | Difference |
| --- | --- | --- | --- |
| SQAT 0.22, per-signal max \|N − workbook\|, signals 6–25 | factorial-matrix `all-tv-cancellation.json` | port cell (0.22, +1e-4) | ≤ 2.2e-8 (the known 1e-8 transient on signals 11–13) |
| Same, against Claude's own SQAT 0.22 run | same | `sqat_0.22` | ≤ 4.9e-9 |
| MoSQITo 0.22 and 0.24, per-signal maxima | same | `mosqito_0.22`, `mosqito_0.24` | 0 |
| Official C (MSVC, binary64 input), per-signal maxima | same | cell (0.22, +1e-4) | ≤ 1.3e-6 (float32 arithmetic inside C) |
| 0.24 against 0.22: improves / worsens / unchanged | SQAT 5,973 / 19,787 / 22,951 | 5,974 / 19,787 / 22,950 | one point on the 1e-12 boundary |
| Calibration × USL interaction, maximum and location | SQAT 1.4443595862e-4, signal 6, 7.44 s | 1.4443595863e-4, signal 6, 7.44 s | < 1e-13 |
| USL main effect (mean over both calibrations), signals 6 / 15 / 16 / 25 | `tv-paired-effects.json` | recomputed from Claude cells with the same definition | ≤ 5e-15, same locations |
| iso532 slope output, signals 2–5 | filter-independent `frontend-results.jsonl.txt` | rebuilt from Astra's levels | 0 (bit-identical) |

Astra defines a main effect as high − low averaged over the other factors. Claude's F1 is at 2√2 only. The two differ by 6e-7 and 4.7e-6 on signals 6 and 15. Recomputed with Astra's definition they agree within 5e-15.

## 3. Astra's 2026-11-05 downstream residual is the ZUP constant

Astra fed the 28-band levels of the Annex front end into both the iso532 slope stage and the official C downstream. N′ still differed, and the report states that the finer downstream mechanism was not traced in that round. This round recomputes it from Astra's delivered levels with USL 0.22 (both versions give the same result on signals 2–5):

| Signal | Location of max N′ difference | iso532 − C, N′ | port with constant − C, N′ | iso532 − C, N | port with constant − C, N | 1e-4 × band-0 core loudness |
| --- | --- | --- | --- | --- | --- | --- |
| 2 | 2.9 Bark | −1.500e-4 | −3.6e-9 | −6.59e-7 | −6.59e-7 | 0 |
| 3 | 9.3 Bark | −6.18e-5 | 1.7e-7 | 1.47e-7 | 1.47e-7 | 0 |
| 4 | 18.2 Bark | −4.21e-5 | −6.1e-8 | 5.6e-8 | 5.6e-8 | 0 |
| 5 | 2.9 Bark | −5.10e-5 | 2.9e-8 | −1.580e-5 | −3.95e-7 | 1.541e-5 |

The table uses the 2√2 conversion. The calibration-file conversion gives the same values to three significant digits; see `astra_residual.json`.

- **Mechanism in N′.** The constant moves every band's upper edge 1e-4 Bark to the right, and the grid samples on the slopes move with it. On signal 2, N′ falls by 0.15 sone/Bark per 0.1 Bark near 2.9 Bark; times 1e-4 Bark that is exactly 1.5e-4.
- **Mechanism in N.** Same as §4.4 of the Claude factor-attribution round. Band 0 is integrated up to 0.9001 Bark while the other band edges telescope, so N gains exactly 1e-4 × the band-0 core loudness. Band 0 is zero on signals 2–4, so N differs there only at float32 level.
- **The remaining ≤ 6.6e-7** is the official C program's binary32 constants and arithmetic. Switching the port to binary32 constants as well brings the N′ difference to ≤ 1.1e-7.

The "total N differs from C by at most about 1.59e-5" statement in Astra's report is the signal-5 row.

## 4. Where the "error cancellation" applies

The headline of Astra's factorial-matrix report is that combinations do show error cancellation and interaction, and that changing one cell does not guarantee a lower overall maximum. The example is MoSQITo signal 15 at 9.606 s: the error with 0.22 is +0.02328, 0.24 adds −0.00039, leaving +0.02289. These numbers equal Claude's MoSQITo results to every digit.

The effect needs a pre-existing residual that is independent of F1 and large enough. Per back end:

| Back end | Max error with 0.22, signals 6–25 | Largest improvement by 0.24 | Points improving by more than 1e-4 |
| --- | --- | --- | --- |
| Official C, SQAT, iso532 with the constant | 7.9e-5 to 8.1e-5 | 5.75e-5 (Claude cell) | 0 |
| MoSQITo 1.2.1 | 0.0233 | not computed per point; 596 points improve on signal 15 | yes, e.g. 3.9e-4 at the signal-15 maximum |

On the official program's path, the 0.22 residual is already within the 4-decimal quantization, so the "improvements" from 0.24 are rounding noise. F1 and F2 add, with interaction ≤ 3e-7 (Claude round §4.3). The calibration × USL interaction peaks at 1.44e-4, more than two orders of magnitude below either main effect; it is a second-order effect of the loudness nonlinearity.

Astra's "596 improve, 5,110 worsen" on signal 15 is MoSQITo. On the same signal SQAT gives 217 / 5,490, the official C 220 / 5,487, and the Claude cell 217 improvements.

## 5. What each side adds

**Astra has, Claude did not run:**

- **float32 input quantization.** The official CLI reads WAVs as float32. Astra measured that f64↔f32 changes N by up to 8.42e-5 on signal 14. This is a plausible source of the ≤ 8e-5 that binary64 implementations still leave against the workbooks; it was not tested here.
- **MoSQITo rounding.** The slope stage rounds N to 0.001 / 0.01 sone. The effect on N is up to 1.39e-3 and N′ is bit-identical; removing it leaves the main signal-15 residual. This is part of what Claude grouped as F7.
- **Filter history and skip.** With the filter history kept, skip 0→0.2 s changes signal 3 by −0.095%. Cropping the input and resetting the filter is a different quantity. Front end × skip interacts (signal 2: −0.0027 sone). This matches the Claude round's "Annex A front end without skip within 0.094%".
- **Decisive-point count correction.** Of the 12,287 points, 12,062 are closer to 0.22 and 225 are equidistant; the earlier 12,109 counted 47 equidistant points as closer to 0.22.
- **SQAT 0.22 against the full-precision official C** reaches 2.0e-6, the total of the float32 arithmetic inside C. The Claude round switched only the slope-stage binary32 constants (≤ 9e-7). The scopes differ and the results are consistent.

**Claude has, Astra's matrix did not include:**

- **The ZUP band-edge constant.** Astra folded it into the "engine" difference; §3 above attributes Astra's own residual to it.
- **iso532 itself.** Astra's matrix back ends are the official C, SQAT and MoSQITo; iso532 appears only as the stationary downstream of the 2026-11-05 round. The 2.19e-4 left on the iso532 time-varying path with 0.22 is explained only by F2.
- **Nonlinear-decay initial state.** Zero effect on Annex B.

## 6. Combined root causes (time-varying signals 6–25 against the workbooks)

| Implementation | Max error as shipped | Composition |
| --- | --- | --- |
| Official C (CLI) | ≤ 1e-4 | the program that produced the workbooks; the difference is the 4-decimal display only |
| SQAT v2.0 | 0.0169 | F1 only; with 0.22 it is 7.9e-5, the rest being float32 input and arithmetic plus 4-decimal quantization |
| iso532 0.4.0 | 0.0169 | F1 plus F2; 2.19e-4 with 0.22, identical to SQAT 0.22 once the constant is added |
| MoSQITo 1.2.1 | 0.0229 | F1, F2, rounding (≤ 1.39e-3), plus F-04…F-07 (about 0.023 on signal 15); the stationary path also has front-end error (up to 0.0808) |

On stationary signals 2–5 the main cause is the front end for all four; USL has no effect on 2–5. The ZUP constant changes N on signal 5 by only 1.5e-5 but moves N′ by up to 1.5e-4.

## 7. Open points and limits

- The 1e-8 transient difference between SQAT and iso532 on signals 11–13 is still untraced and below every threshold.
- The ≤ 8e-5 that binary64 implementations leave against the workbooks is not decomposed here; Astra's float32 input control covers signals 6, 9, 14 and 15 only.
- The official Table A.9 text is still PENDING on both sides.
- This round is a comparison, not a new independent acceptance. No product code was changed.

## 8. Checks on the Astra deliveries

The three Astra folders were checked before being tracked. `redact_paths.py --check` prints `clean` for each. `delivery-integrity.json` matches the files one by one (39, 67 and 62 files). Most files are CRLF, so, as with the 2026-11-04 round, the three folders are marked `-text` in `.gitattributes` and their bytes stay unchanged. The only non-UTF-8 file is the image `factorial-effects.png`.

## 9. Replay

See [replay.md](replay.md). The scripts read only Astra's delivered files, the Claude factor-attribution round's `results.json` and cell outputs, and the workbooks.
