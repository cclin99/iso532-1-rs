# Independent contract and record checks

Run `python run_contracts.py <repository-root>` in an environment containing NumPy and openpyxl. The script reads the frozen archives in `tmp/acceptance-040-astra`, copies each frozen Cargo.lock into the external harness before resolution, and delivers the resulting harness lockfiles. It never modifies product sources. Run `python audit_sig15.py <repository-root>` afterward for the read-only OOXML spot check.

## Contract result: PARTIAL, no detected regression

- Both versions pass all 73,116 individual Annex B total/specific reference points across signals 1–25, under the brief's strict per-point `max(0.1, 0.05*abs(reference))` rule. This count covers the reference curves and stationary Bark values, not the workbook's derived Nmax/N5 summary metrics. Signal 15 is diffuse field as explicitly specified in its worksheet A1; all other sheets specify free field.
- The minimum margin is identical: 0.059702781183555126, signal 2 specific loudness index 9 (1.0 Bark), computed 0.3688972188164449 (`3fd79c031499ba26`) against 0.3286 (`3fd507c84b5dcc64`). It is worksheet `Test signal 2`, cell G17.
- A preliminary harness incorrectly treated signal 15 as free field. The worksheet audit caught this configuration error; the final harness was corrected and both versions were rerun. The preliminary failures are not product findings. The OOXML audit preserves title, tolerance formulas and a directly checked reference row.
- The workbook's C/D bounds use adjacent-point envelopes, and its separate G/H columns use a wider tolerance. The formal comparison here uses the stricter frozen per-point rule, without substituting either workbook envelope or exception allowance.
- Signals 10/18/23/25, custom chunks `[1,193,7,4097,24,97,2,511]`: 4,136 frames per version. Batch and stream total loudness have zero differing f64 bits. Time derived from the public stream frame index as `96*j/48000` also has zero differing bits against batch time_axis. The stream API itself has no floating-point time_axis field.
- Seven requested output-grid lengths pass in both versions.
- Public StreamFrame in **both** versions has no n_specific. The requested stream-specific bitwise comparison is therefore **PARTIAL**. This is a pre-existing public API limitation, not a release regression; the harness does not instrument private state or manufacture a specific output.
- Both headers have SHA-256 `2f1b299a8c3a162ca3dda68b2899ed602c7c28f8c1d4e9a8fa409dfde38b3661`; both compiled DLLs expose the same nine names. DLL raw hashes and exports are in contracts-results.json.

## Record findings

All three Cargo.toml and Cargo.lock package versions are 0.4.0. CITATION.cff remains 0.3.1 as disclosed. The 0.4.0 changelog includes F-04 through F-07 and Annex A, and the CI py job contains HASH_GATE_DUMP_ONLY.

The release commit table omits `5bbbb93228b9972c0277415bebd565364de974fc` (`docs: fix the pair line of the English slope-alignment decision memo`). The queried range has twelve commits; eleven are represented, including the self-referential final release-record commit. This is a documentation discrepancy, not a numerical defect. Parent verification integrates this with the other release-record numerical checks.

## Delivery checks

The subdirectory redactor replaced three paths in each harness log and one in run.log (three files changed); a subsequent `--check` returned `clean`. No skipped/format warnings were printed by that pass. Every delivered file was decoded as UTF-8, with only `.py`, `.txt`, `.json`, `.log`, and this `.md` present; no binary output, workbook, WAV, or cache directory is delivered. The openpyxl conditional-formatting warning in run.log concerns unsupported workbook formatting while opening in read-only mode; no workbook was saved or altered. Parent verification performs the final whole-delivery redaction and integrity manifest.

Input hashes describe original WAV/workbook/source bytes; decoded input and raw output hashes describe the local binary arrays, not the redacted text evidence. The JSON also includes negative controls for one-bit mismatch detection and rejecting 10.55 versus 10 under the frozen tolerance rule.
