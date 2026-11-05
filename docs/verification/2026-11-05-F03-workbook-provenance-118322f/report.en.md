# F-03: the Annex B workbooks were produced with `USL[12][4]` = 0.22

> 對照／Pair: [中文版](report.md) · source: zh · synced 2026-11-05

Claude (Opus 5.5, main agent, not Astra), 2026-11-05 Asia/Taipei. Against: `v0.4.0` = `118322f`. Follows up [`2026-11-05-annexb-bias-118322f/`](../2026-11-05-annexb-bias-118322f/report.en.md) and [`2026-11-05-zwst-root-cause-118322f/`](../2026-11-05-zwst-root-cause-118322f/report.en.md).

## Conclusions

- **SQAT v2.0 cannot serve as evidence for 0.24.** Like MoSQITo it is an implementation, not the standard; the cell is still 0.24 in v2.0 (tag `v2.0` = `94f489c`, line 519), but neither the v2.0 release notes nor PRs #48 / #49 mention Table A.9 or `USL`. It claims to "closely mirror the reference C implementation" while this cell differs from that C program, which shows rather that SQAT did not align the table cell by cell. Whether SQAT and MoSQITo are independent cannot be established.
- **The filter root cause is unrelated to 0.24.** The front-end error and the conversion convention act on the band levels; `USL` is the upper-slope table of the slope stage. But with both causes known, the workbooks can now be reproduced to 1e-4 sone, which for the first time allows testing directly which value they were produced with.
- **Result: the Annex B workbooks distributed with ISO 532-1 were produced by the official Annex A C program (`USL[12][4]` = 0.22f) with the conversion "full scale 1.0 = 2√2 Pa".**
  - The unmodified official C program on the 2√2-scaled inputs reproduces stationary N of signals 2–4 exactly (signal 5 by 0.0001) and all 240 specific values of the four stationary signals exactly; every time-varying point is within ≤ 0.0001, the rounding of the fourth decimal.
  - The same C program with only this cell set to 0.24f: on the 12,287 points (12 signals) where the two builds differ by ≥ 2e-4 sone, the workbook equals the 0.22 build at **11,174** points and the 0.24 build at **0** points; it is closer to the 0.22 build at 12,109 points (98.6%).
- **So 0.24 is inconsistent with the standard's own reference data, while 0.22 agrees with both executable artifacts distributed with the standard (the C program and the workbooks).** Under the 5% Annex B tolerance both values pass, which is why F-03 could not tell them apart before.
- **This does not yet make 0.22 the normative value of the corrected Table A.9.** The text of Table A.9 is still unavailable; this C attachment carries ISO_DIS / 2016 marks, and the content of the 2017-11 correction is unknown. In principle the correction could have changed the printed table to 0.24 without updating the attachments. That would leave the printed table contradicting the standard's own reference program and reference data, which is clearly less likely. This is an inference.

## 1. Method

1. [make_float_wavs.py](make_float_wavs.py): Annex B signals 2–25 converted to `int16 / 32768 × 2√2` Pa and written as 32-bit float WAVs (the official CLI needs no calibration file for float WAVs).
2. Two CLIs built from the official sources (MSVC x64, `/O2 /fp:precise`, [build-v022.cmd.txt](build-v022.cmd.txt), [build-v024.cmd.txt](build-v024.cmd.txt)):
   - `v022`: unmodified, `ISO_532-1.c` SHA-256 `a74b45ed…`.
   - `v024`: only `USL[12][4]` changed from 0.22f to 0.24f, identical to `tools/golden-c-usl12-4.diff`, SHA-256 `739af24d…`. Both hashes equal those recorded in the 0.4.0 release record.
   - Control: the fresh `v022` build produces `Loudness.csv` and `SpecLoudness.csv` byte-identical to the earlier round's `reference_cli.exe` on all 24 signals.
3. [run_two_cli.py](run_two_cli.py): both CLIs run once (stationary signals 2–5 with time skip 0.2 s; time-varying signals 6–25, signal 15 diffuse field) and their output (fourth decimal) is compared point by point with the workbooks.
4. [decisive_points.py](decisive_points.py): only points where the two builds differ by ≥ 2e-4 sone. That difference exceeds what rounding of the fourth decimal can produce, so at these points "the workbook equals which build" tells which build produced it.
5. [compare.py](compare.py): the 0.4.0 wheel (Rust, 0.24) on the same inputs, as supporting evidence.

## 2. Results

### 2.1 All points ([two-cli-compare.json](two-cli-compare.json))

- 49,675 compared points, 15,801 where the builds differ in the fourth decimal: the workbook equals the 0.22 build at 14,277, the 0.24 build at 411, neither at 1,113.
- At the 411 points equal to the 0.24 build the two builds differ only in the last digit, on a rounding boundary; this level alone does not decide, §2.2 does.
- Largest difference of `v022` to the workbook: ≤ 0.0001 for every signal. `v024` reaches 0.0169 (signal 6).

### 2.2 Decisive points (builds differ by ≥ 2e-4, [decisive-points.json](decisive-points.json))

| signal | points | workbook = 0.22 build | workbook = 0.24 build | closer to the 0.22 build |
|---|---:|---:|---:|---:|
| 6 (250 Hz ramp) | 1,292 | 1,242 | 0 | 1,291 |
| 9 (pink noise ramp) | 998 | 891 | 0 | 968 |
| 14 (propeller aircraft) | 3,453 | 3,098 | 0 | 3,427 |
| 15 (vehicle interior, diffuse) | 4,359 | 3,950 | 0 | 4,280 |
| 16 | 1 | 1 | 0 | 1 |
| 17 | 89 | 83 | 0 | 85 |
| 18 | 299 | 265 | 0 | 288 |
| 19 | 825 | 758 | 0 | 818 |
| 20 | 121 | 104 | 0 | 110 |
| 21 | 5 | 5 | 0 | 5 |
| 23 | 144 | 124 | 0 | 137 |
| 24 | 701 | 653 | 0 | 699 |
| **total** | **12,287** | **11,174 (91%)** | **0** | **12,109 (98.6%)** |

Where the workbook does not equal the 0.22 build exactly (9%), the difference is also only 0.0001. A plausible cause is that the workbooks were computed from the int16 WAVs while float32 WAVs were used here, plus rounding boundaries; this is an inference and was not verified.

### 2.3 Supporting evidence: Rust 0.4.0 (0.24)

[compare.json](compare.json): at the points where Rust and the 0.22 C build differ by ≥ 2e-4, the workbook is closer to C at every point (for example 3,623 / 3,623 for signal 14 and 5,151 / 5,151 for signal 15) and never equal to Rust. This agrees with §2.2: the difference between Rust and the 0.22 C build does come from this cell.

## 3. What this means for F-03

| earlier finding | now |
|---|---|
| Annex B cannot tell 0.22 from 0.24 (5% tolerance) | the tolerance verdict is unchanged; at 1e-4 sone precision the workbooks agree with 0.22 only |
| primary sources for 0.22: the official C attachment, the 1991 BASIC paper, MetaSona | plus the Annex B workbooks, which are output of that C attachment |
| sources for 0.24: MoSQITo, SQAT (v1.0 / v1.3 / main) | plus SQAT v2.0; all still implementations, no standard source |
| content of the Table A.9 correction unknown | still unknown |

## 4. Options (to be decided)

| option | content | impact |
|---|---|---|
| **A (recommended)**: change to 0.22 | agrees with the official C program and the workbooks; the C golden can be produced by the unmodified official program, with no "one-cell exception" | numeric change; can join the ZWST front end in 0.5.0; the gap to MoSQITo grows by up to about 0.017 sone at the affected points |
| B: keep 0.24 | keeps MoSQITo / SQAT compatibility | documentation must state the disagreement with the standard's own reference data at about 12,000 points, up to 0.0169 sone |
| C: obtain the Table A.9 text first | buy the corrected 2017-11 standard | the only way to close the authority gate; does not change the data behind A or B |

D3 (2026-11-03) kept 0.24 "provisionally" with the condition "if the text later proves 0.22". The new evidence is not the text but the reference data distributed with the standard; whether that is enough to change the value is your judgment. My assessment: the weight of evidence now clearly favours 0.22, and with 0.22 "agrees with Annex A" needs no exception and the CITATION wording becomes cleaner.

## 5. Limits

- The workbooks and the C attachment come from the same archived package (`tmp/c01-material/official/`); how that attachment (ISO_DIS / 2016 marks) relates to the corrected 2017-11 edition is still open.
- Only time-varying N(t) and stationary N and N′ were compared; the N′(t) curve in the workbooks of signals 6–13 was not compared point by point between the 0.22 and 0.24 builds.
- The float WAVs are float32 and may differ from the original int16 path at the 1e-7 level, which does not affect fourth-decimal decisions.

## 6. Evidence files

| file | content |
|---|---|
| [make_float_wavs.py](make_float_wavs.py), [float-wavs.json](float-wavs.json) | 2√2-scaled float WAVs and their hashes |
| [build-v022.cmd.txt](build-v022.cmd.txt), [build-v024.cmd.txt](build-v024.cmd.txt) | build commands of the two official CLIs |
| [run_two_cli.py](run_two_cli.py), [two-cli-compare.json](two-cli-compare.json) | full comparison of both builds with the workbooks, and the control |
| [decisive_points.py](decisive_points.py), [decisive-points.json](decisive-points.json) | decisive points where the builds differ by ≥ 2e-4 |
| [compare.py](compare.py), [compare.json](compare.json) | Rust 0.4.0 supporting evidence |
| [sources-and-hashes.json](sources-and-hashes.json) | SQAT v2.0 check (tag, commit, line number, line content), hashes of official sources / CLIs / workbooks, hashes of the CLI outputs not delivered |
| [delivery-integrity.json](delivery-integrity.json) | SHA-256 of each file after redaction (excluding itself) |

WAVs, CLI executables and CLI outputs stay in `tmp/` and are only hashed; the SQAT GPL source is not included, only the one line is quoted.
