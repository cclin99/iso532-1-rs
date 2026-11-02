# Independent numerical acceptance reproduction

Run from the repository root after the parent freezes source at `tmp/acceptance-031/source` and baseline at `tmp/acceptance-031/baseline`, with verified Annex/golden data available in source:

```powershell
python docs/verification/2026-11-02-release-0.3.1-30e4279/numerics/run.py --repo .
$env:CARGO_BUILD_JOBS='2'
$env:CARGO_TARGET_DIR=(Join-Path (Get-Location) 'tmp/acceptance-031/numerics-hash-target')
$env:HASH_GATE_DUMP_ONLY='1'
$env:REQUIRE_AVX2='1'
cargo test --offline --manifest-path tmp/acceptance-031/source/Cargo.toml -p iso532 --test hash_gate -- --nocapture *> docs/verification/2026-11-02-release-0.3.1-30e4279/numerics/hash-gate.log
python docs/verification/2026-11-02-release-0.3.1-30e4279/numerics/augment.py --repo .
```

The source archives and version/toolchain evidence are owned by the parent report. The annotated v0.3.0 tag object is `749dac1933c160d8bbd0592e7be31397af8513ab`; its peeled source commit is `62e46ca7d6ac65df7c4a4db8df8380e30234e267` (`git rev-parse 'v0.3.0^{commit}'`). The baseline archive uses that commit; results record tag object and commit separately. `run.py` builds separate path-dependent binaries, includes the exact frozen validator/common module, writes binary intermediates only under `tmp/`, and retains SHA-256 values of input WAV, prepared binary64 signal, binary outputs and executable files. Supplied lockfiles pin the independent harness dependencies when reproducing. No source/golden/test file is altered.

WAVs are decoded using scipy.io.wavfile; signed PCM is normalized by its container bit width (SciPy left-justifies 24-bit PCM), calibration is 2*sqrt(2), multichannel would be averaged, and non-48-kHz inputs are resampled using scipy.signal.resample_poly. This preprocessing is shared by both releases, is explicitly a finite-invariance fixture preparation, and is not an official C numerical acceptance claim. The 3-second signal is generated directly from the frozen `tools/iso532_testkit.py` used by compare_mosqito.py; MoSQITo is not run or used as reference.

The five true Annex reference comparisons use the existing calibrated `sig.bin` inputs and official CSV/reference binaries, and call the frozen verdict independently. The minimum margin spans all points of these five curves (982 points), not only maxima. Stationary results have no time_axis; the five fields per input are stationary n/n_specific and time-varying n/n_specific/time_axis. Coordinates for a hypothetical specific-loudness mismatch are zero-based Bark row/frame. No mismatch occurred.

`augment.py` checks all four printed hash tuples against constants extracted from Windows cfg sections of the frozen hash_gate source; dump-only success is never treated as evidence of tuple equality by itself. It also audits the five Annex call sites and adds corrupted binary-copy controls. Direct boundary cases preserve exact binary64 diff/tolerance hex in validator-controls.log.

All delivery files are UTF-8 text. Binary hashes retain their original raw meanings. Parent performs final redaction, explicit review of unhandled extensions (including rs and lock), and delivery integrity hashing. Reproduction logs overwrite this subfolder's files; reproduce in a new delivery folder for another independent round.
