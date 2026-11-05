# Root cause of the ZWST error against Annex B

> 對照／Pair: [中文版](report.md) · source: zh · synced 2026-11-05

Claude (Opus 5.5, main agent, not Astra), 2026-11-05 Asia/Taipei. Tested: the `iso532` crate of `v0.4.0` = `118322f` (the main-tree `iso532/` is byte-identical to the tag). Follows up [`2026-11-05-annexb-bias-118322f/`](../2026-11-05-annexb-bias-118322f/report.en.md).

## Conclusions

- **The ZWST error comes entirely from the spectrum front end.** ZWST deliberately keeps the `noct_spectrum` of MoSQITo 1.2.1 (6th-order Butterworth band-pass filters designed per ANSI S1.1-1986), while ISO 532-1 Annex A uses the standard's own reference filters (Tables A.1 / A.2). The two have different design goals:
  - The Annex A filters attenuate exactly **−20.00 dB** at the neighbouring band centres, and their effective noise bandwidth is 2.0% to 4.2% wider than an exact third octave.
  - The MoSQITo filters align the effective noise bandwidth with an exact third octave (1.000), at the cost of only **−19.4 dB** at the neighbouring band centres, degrading to −17.5 dB at high frequencies.
- **These two differences fully explain the observed error:**
  - Pure tones: about 0.6 dB more energy leaks into the **lower** neighbouring bands. The Zwicker model has no masking slope on the low side, so that energy goes straight into loudness: +0.23% to +0.82%. Leakage into upper bands is covered by the upper slope and does not change total loudness.
  - Noise: each band's effective bandwidth is about 0.1 dB narrower, so pink noise comes out −0.77%.
- **With the Annex A stationary method** (the same ISO filter bank, mean square from 0.2 s on, i.e. `f_square_and_smooth` in `ISO_532-1.c`):
  - with the calibration-file conversion the result equals the official CLI to four decimals;
  - with the 2√2 conversion all four signals are within ≤ 0.001% of the workbook.
- The time window (skipping the first 0.2 s or not) matters by ≤ 0.002% and is ruled out. Main loudness and slopes were already shown by signal 1 to match the workbook.
- **This is not a bug but a front-end design choice:** the README states that ZWST "deliberately keeps the MoSQITo-compatible spectrum path". Bringing ZWST to the precision of the time-varying path means replacing the front end, a numeric change (§5).

## 1. Method

[zwst_frontend_harness.rs.txt](zwst_frontend_harness.rs.txt) depends on `iso532` by path and computes, for Annex B signals 2–5 (the calibrated inputs of the 2026-11-04 Astra round):

- `noct`: `iso532::zwst::noct_spectrum_rms`, the front end ZWST actually uses.
- `noct_skip0p2`: the same front end, skipping the first 0.2 s.
- `iso`: the ISO filter bank built from `TOB_B`, `TOB_DELTA` and `TOB_GAIN`, mean square from sample 9,600 on, converted to levels.

All three level sets go through the same `main_loudness` and `calc_slopes`. Attribution starts from the `iso` levels and replaces one band at a time with its `noct` value, recording the change in total loudness. Each conversion runs twice: once with the calibration-file factor and once multiplied by 0.997401 (equal to 2√2).

[filter_response.py](filter_response.py) parses the coefficients the two filter banks actually use from the sources (`NOCT_SOS` at 48 kHz / `NOCT_DECIM_Q`; the ISO filters at 48 kHz) and computes their frequency responses.

## 2. Total loudness

| signal | workbook | ISO front end (2√2) | MoSQITo front end (2√2) | MoSQITo front end (calibration file) | official CLI (calibration file) | ISO front end (calibration file) |
|---|---:|---:|---:|---:|---:|---:|
| 2 (250 Hz 80 dB) | 14.6545 | 14.6545 (+0.000%) | 14.6888 (+0.234%) | 14.7105 (+0.382%) | 14.6761 | 14.6761 |
| 3 (1 kHz 60 dB) | 4.0192 | 4.0192 (−0.001%) | 4.0523 (+0.823%) | 4.0589 (+0.987%) | 4.0257 | 4.0257 |
| 4 (4 kHz 40 dB) | 1.5494 | 1.5494 (−0.001%) | 1.5560 (+0.424%) | 1.5582 (+0.569%) | 1.5516 | 1.5516 |
| 5 (pink noise 60 dB) | 10.4978 | 10.4978 (+0.000%) | 10.4173 (−0.767%) | 10.4336 (−0.611%) | 10.5143 | 10.5143 |

"MoSQITo front end (calibration file)" is the current ZWST error; it splits into the conversion convention (about +0.15%) plus the front-end difference (−0.77% to +0.82%). Skipping 0.2 s changes the full-signal RMS result by ≤ 0.002% (`n_noct_skip0p2` in [levels-2sqrt2.jsonl.txt](levels-2sqrt2.jsonl.txt)).

## 3. Band attribution (2√2 conversion)

| signal | most influential band | ISO level | MoSQITo level | difference | ΔN from swapping this band |
|---|---|---:|---:|---:|---:|
| 2 | 158 Hz (second band below the tone) | 41.33 | 42.54 | +1.21 dB | +0.0316 sone |
| 2 | 200 Hz (first band below) | 60.56 | 61.08 | +0.52 dB | +0.0036 |
| 3 | 794 Hz (first band below) | 40.00 | 40.61 | +0.60 dB | +0.0193 |
| 3 | 631 Hz (second band below) | 21.03 | 22.01 | +0.98 dB | +0.0097 |
| 3 | 501 Hz (third band below) | 9.29 | 11.01 | +1.71 dB | +0.0045 |
| 4 | 3.16 kHz (first band below) | 19.37 | 19.82 | +0.45 dB | +0.0066 |
| 5 | each band 1.6–6.3 kHz | ≈ 42.8 | ≈ 42.7 | −0.10 to −0.12 dB | about −0.005 each |

The band containing the tone has the same level in both (difference ≤ 0.005 dB). The single-band swaps add up to the ΔN of the whole front-end difference (signal 2: +0.0352 against +0.0343; signals 3 and 4 identical; signal 5: −0.0801 against −0.0805).

## 4. Filter characteristics ([filter-response.json](filter-response.json))

| bands | effective noise bandwidth ÷ exact third octave: ISO / MoSQITo | bandwidth ratio (dB) | attenuation at lower neighbour centre: ISO / MoSQITo | attenuation at upper neighbour centre: ISO / MoSQITo |
|---|---|---:|---|---|
| 25 Hz–1 kHz (0–16) | 1.020–1.022 / 1.000 | −0.085 to −0.094 | −20.00 / −19.39 to −19.40 | −20.00 / −19.40 to −19.41 |
| 1.26–5 kHz (17–23) | 1.022–1.026 / 0.999–1.000 | −0.096 to −0.112 | −20.00 to −20.04 / −19.13 to −19.38 | −20.00 to −20.09 / −19.42 to −19.84 |
| 6.3–12.6 kHz (24–27) | 1.029–1.042 / 0.995–0.999 | −0.129 to −0.192 | −20.00 / −17.50 to −18.97 | −20.00 to −22.48 / −20.11 to −23.30 |

The leakage difference predicted from the filter responses agrees with the band differences measured in §3: for the 1 kHz tone in the 794 Hz band, predicted +0.59 dB, measured +0.60 dB; for the 4 kHz tone in the 3.16 kHz band, predicted +0.43 dB, measured +0.45 dB. The high-frequency degradation of the MoSQITo filters looks like the frequency compression of the bilinear transform (a comment in the MoSQITo source says BUTTER uses the bilinear transform); this is an inference and was not verified separately.

## 5. Options (to be decided; no code change in this round)

| option | content | impact |
|---|---|---|
| A. ZWST defaults to the Annex A stationary method | reuse the ISO filter bank plus mean square; decide how the time skip is set (the official CLI takes it from the user, the workbooks correspond to 0.2 s) | numeric change, 0.5.0; the Annex B error drops from 0.2%–0.8% to ≤ 0.001% (2√2 conversion); the ZWST gap to MoSQITo becomes 0.2%–0.8% |
| B. Add an Annex A stationary function, keep the current ZWST | for example a separate function or option, following the `NlInit::MosqitoTail` pattern | new feature, 0.5.0; current output unchanged; users choose |
| C. Keep as is, document only | state the size and cause of the front-end difference in the README | no version change |

My recommendation is **A, keeping the MoSQITo-compatible front end as an option**. D1 of 0.4.0 already makes Annex A the correctness reference and the time-varying path was aligned with it; keeping a different front end for the stationary path is inconsistent, and following the `NlInit::MosqitoTail` pattern still serves users who need to compare with MoSQITo. This is the "stationary front end undecided" item; it should follow the 0.4.0 process: decision memo, phase plan, implementation, then Astra acceptance.

## 6. Limits

- Only the four stationary Annex B WAV signals (2–5) were used; for other stationary inputs the size of the error depends on the spectrum shape, but the mechanism is the same.
- The frequency responses are theoretical responses of the parsed coefficients; ZWST decimates before filtering the low bands, and the effect of the decimation filter was not isolated (the bands that matter most for signals 2–5 mostly need no decimation; only the 158/200 Hz bands of signal 2 use q = 2).
- "The high-frequency degradation of the MoSQITo filters comes from the bilinear transform" is an inference.

## 7. Evidence files

| file | content |
|---|---|
| [zwst_frontend_harness.rs.txt](zwst_frontend_harness.rs.txt), [zwst_frontend_harness.Cargo.toml.txt](zwst_frontend_harness.Cargo.toml.txt) | front-end comparison and band-swap harness |
| [levels-calfile.jsonl.txt](levels-calfile.jsonl.txt), [levels-2sqrt2.jsonl.txt](levels-2sqrt2.jsonl.txt) | 28 band levels, N and per-band ΔN for both conversions |
| [filter_response.py](filter_response.py), [filter-response.json](filter-response.json) | frequency responses of both filter banks |
| [delivery-integrity.json](delivery-integrity.json) | SHA-256 of each file after redaction (excluding itself) |
