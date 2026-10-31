# F-01: Annex A low-frequency correction skipped the last DLL row

> 對照／Pair: [中文版](F01-LOW-FREQ-DLL-ROW-FIX-2026-10-31.zh-TW.md) · source: en · synced 2026-11-01

- Date: 2026-10-31
- Scope: `iso532/src/core/main_loudness.rs` (`main_loudness_unchecked`), shared by
  batch ZWST, batch ZWTV, and `ZwtvStream` (via `main_loudness_clamped`)
- Origin: finding F-01 of `docs/修正報告.md` (independent audit against the official
  ISO 532-1 Annex A C program), verified and fixed in this change; post-fix independent
  verification in `docs/修正後獨立驗證報告.md`
- Status: fixed; numeric behaviour change on a bounded input domain
- Framing: the MoSQITo comparison below is a finding made during verification plus this
  project's current judgment; it is not a verdict on MoSQITo

## Finding

ISO 532-1 Annex A (`corr_third_octave_intensities`, identical to the Zwicker/Fastl
1991 BASIC program) selects the RAP range for each of the 11 low bands with

```c
j = 0;
while (j < 7 && level > RAP[j] - DLL[j][band]) j++;
corrected = level + DLL[j][band];
```

so any level above the seventh threshold receives the last row, `DLL[7]`.

The Rust port mirrored MoSQITo 1.2.1, whose vectorised replacement of that loop iterates
`for i in arange(1, dll_mat.shape[0] - 1)` and therefore does not reach row 7. Above the
seventh threshold the pre-set value `0` remained as the correction. The same loop is
present on MoSQITo upstream `master` (checked 2026-10-31; last upstream commit
2024-04-22). Current judgment: follow Annex A, the reference both projects cite.

Affected domain (level strictly above `RAP[6] - DLL[6][band]`, up to the 120 dB
validity limit):

| band | centre | threshold | correction before | correction after (Annex A) |
|---|---|---:|---:|---:|
| 0 | 25 Hz | 118 dB | 0 | -15 dB |
| 1 | 31.5 Hz | 112 dB | 0 | -10 dB |
| 2 | 40 Hz | 109 dB | 0 | -8 dB |
| 3 | 50 Hz | 106 dB | 0 | -4 dB |
| 4 | 63 Hz | 102 dB | 0 | -2 dB |
| 6 | 100 Hz | 103 dB | 0 | -3 dB |
| 7 | 125 Hz | 101 dB | 0 | -1 dB |
| 9 | 200 Hz | 101 dB | 0 | -1 dB |

Bands 5, 8, and 10 have `DLL[7] = 0` and were never affected. Levels at or below the
seventh threshold take the same row as before; because every band's thresholds are
strictly increasing (now pinned by a unit test), the old xor formulation and the Annex A
loop agree bitwise there.

## Reproduction (before / after)

Reference values are from the official ISO 532-1 Annex A C program as executed by the
independent audit (`docs/修正報告.md` §3.2; the C sources are not redistributed in this
repository). The 28-band value was re-derived here by running the Annex A loop
against the crate's own tables.

| Case | Before | After | Annex A C | Tolerance (max(0.1, 5 %)) |
|---|---:|---:|---:|---|
| 28 bands, band 0 = 118.000001 dB, others -60 dB, free | 154.93 sone | 52.51 sone | 52.514908816 | pass |
| 2 s sine, 25 Hz, 119 dB SPL, ZWST free | 165.19 sone | within tolerance | 56.704172426 | pass |
| same sine, ZWTV max N | 172.13 sone | 56.877 sone | 56.878693537 | pass |
| same sine, stream max N after warm-up | 171.97 sone | 56.555 sone | 56.878693537 | pass (window after onset) |

The stream and batch values agree frame by frame after warm-up to <= 1e-6 (<= 1e-9 only
from frame 597 on this signal; `N_WARMUP_FRAMES = 580` was frozen on the synthetic test
signal and is not changed here).

## Fix

`low_freq_dll_row(level, band)` implements the Annex A loop verbatim and replaces the
xor-based selection. No table, threshold direction, power conversion, or later stage
was touched.

## Verification added

- Unit (`main_loudness.rs`): thresholds strictly increasing per band; row selection at
  every threshold, one ULP below, and one ULP above, for all 11 bands and 8 rows;
  saturation at row 7 and at row 0; NaN maps to row 0 (documented, not an endorsement
  of non-finite input); the last row is reachable below 120 dB; the clamped stream
  variant equals the batch variant at 119 dB.
- Integration (`tests/low_freq_correction.rs`, self-contained, added to CI): the four
  reproduction rows above, the 118 dB strict-threshold step, the 120 dB acceptance /
  120 dB + ULP rejection contract, diffuse field, and stream-vs-batch tracking after
  warm-up.
- Regression: the nine MoSQITo golden fixtures, Annex B signals 3/5/10, SIMD parity,
  determinism, the frozen hash gate, FFI, and the Python parity suite (see the commit
  message for the run record).

## Consequences

- MoSQITo 1.2.1 parity is now scoped: it holds outside the domain above. Inputs with
  low-band levels above the seventh threshold are expected to differ from MoSQITo and
  must be judged against Annex A.
- The panel (`iso532-rs-panel`) pins core `v0.1.0` by git tag and is not changed by
  this commit; it keeps the old behaviour until its dependency is bumped.
- F-02 (batch nonlinear-decay seed from the final frame) is a separate, documented
  MoSQITo-compatibility choice and is intentionally not touched here.
