# C-01 experiment design — preregistered

Date: 2026-11-03 (Asia/Taipei). Independent verifier: Astra. Tested commit: `aa379db8f3dc37f5048ac6c8b7a6d4ba2a6c3b76` (`aa379db`). This design is written before any numerical run. Pair: [Traditional Chinese](experiment-design.md).

## 1. Question and hypotheses

H1: For Annex B signals 18, 23, 24 and 25, the final unpadded Rust batch value agrees with the previously unavailable official C internal frame K when the input is padded. H2: padding leaves every earlier official C internal frame bitwise unchanged. H3: measured library/CLI/Rust shapes follow the three distinct output-grid formulas. This experiment tests a remaining numerical gap, not universal ISO compliance or a choice between F-03 coefficients.

## 2. Frozen material and method

Extract an isolated source snapshot from the fixed commit under `tmp`; inventory source hashes before building and after running. Keep harness files separate. Recover the archived official Annex A source and Annex B WAVs from the locally retained official archive; record archive/WAV/header/CLI/library hashes. Require `ISO_532-1.c` SHA-256 `a74b45ed297cd09ac60701a923120341137d227e536f3109ae4ece810d834491`. Build unchanged C and CLI using MSVC `/nologo /O2 /fp:precise`, as in the 2026-10-31 reference build; `_CRT_SECURE_NO_WARNINGS` is only a CRT diagnostic definition. A separate wrapper may call and export official routines; no DSP constants, calculation bodies or loop bounds may change.

Decode mono 48 kHz PCM16 as signed little-endian integer / 32768. Use the Annex C 60 dB calibration file and the official CLI's sequential intensity accumulation and pressure scaling. Export the calibrated binary64 samples once; pass identical bytes to C and Rust. Record decoded, calibrated, padded and original WAV hashes, finite counts, channels, rate, sample width, calibration factor and encoding. The CLI independently reads PCM WAVs with the same calibration; require its decoder/calibration pressure bytes to match the library input. Append only PCM zero samples for CLI padding and binary64 zeros for library padding.

## 3. Primary comparison and locked thresholds

For each original length L, K=floor(L/24), L_pad=96*(ceil(L/96)+1), j=K/4. Assert K mod 4=0 and L mod 24>0. Run official C on original and padded pressure samples at 48 kHz, time-varying, free-field. C library reference is undecimated padded total[K] and specific[b,K] for all b=0..239. Compare Rust loudness_zwtv on the original pressure input at j=frames-1. Require matching shapes and all finite values before subtraction. Preserve decimal strings with 17 significant digits and binary64 bits for all 241 values on both sides; report each difference and maximum.

AGREES requires total absolute difference <=1e-14 sone AND every specific difference <=1e-14 sone/Bark. WITHIN TOLERANCE is a fallback only when all differences satisfy max(0.1,0.05*abs(reference)); otherwise DIFFERS. NOT OBTAINABLE means the official reference cannot be obtained. Do not loosen thresholds after seeing results. CLI text is a serialization/grid check only: require data row j to exist in both padded outputs, correct time j*0.002, 240 specific columns, and four-decimal serialization consistent with library values (absolute error <=0.000050000001). It cannot decide the 1e-14 gate.

## 4. Controls and expected boundary table

For every signal compare ALL C internal frames 0<=k<K, including non-output frames. For total and specific separately record compared count, bitwise mismatch count, maximum absolute difference and first differing coordinate. H2 requires zero mismatches. Inject +1e-6 into one finite specific value in a reference copy; the SAME primary comparator must return non-AGREES and the injected coordinate. Original arrays remain unchanged. Additionally check finite/shape rejection paths to prevent invalid data passing.

Use the first 4897 samples of Annex B signal 18 as the common boundary base, hash it, and take prefixes of the following lengths. Measure actual C return count, actual CLI data rows, and actual Rust n/spec/time lengths; do not substitute formulas for observations.

| L | C frames | CLI total | CLI specific | Rust n/time | Rust specific elements |
|---:|---:|---:|---:|---:|---:|
|4800|200|50|50|50|12000|
|4801|200|50|50|51|12240|
|4823|200|50|50|51|12240|
|4824|201|50|51|51|12240|
|4825|201|50|51|51|12240|
|4895|203|50|51|51|12240|
|4896|204|51|51|51|12240|
|4897|204|51|51|52|12480|

Run the fixed snapshot's `cargo test -p iso532 --test output_grid --locked --offline` as supporting contract evidence. No source changes, golden regeneration, benchmark, binding/package/full-suite acceptance, audit-row edits, commit or push.

## 5. Decision and delivery

Recommend closing only this round's numerical gap if four primary comparisons, all prefix controls, comparator control, finite/shape/input gates and eight boundary rows pass. Keep passed/failed/blocked/skipped/partial distinct. Broader C-01 audit closure (including reset/flush/short-input requirements) remains a separate decision. A failed required gate prevents closure even if Annex B fallback passes.

Deliver matching bilingual design/reports, results.json, scripts, raw selected-point CSV, commands/logs/exit codes/versions, source/input/binary hashes, delivery-check.md and final delivery-integrity.json. Only UTF-8 text is delivered; WAVs and binaries stay in tmp. Run path redaction and --check, inspect unsupported extensions and warnings, review delivery diff, rerun both passes after all text is finished, then hash final files excluding the integrity manifest itself. Original material hashes retain their original meaning.
