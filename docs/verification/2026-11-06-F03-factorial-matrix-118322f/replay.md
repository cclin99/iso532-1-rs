# Reproduce the factorial matrix

Run from the repository root. Delivery: `docs/verification/2026-11-06-F03-factorial-matrix-118322f/`; new scratch: `tmp/verification-f03-factorial-matrix/`. Do not overwrite either prior verification round. Product tag snapshot is `118322f8300dc752f1d38a79db230a2db5ff2870`; source-code differences to the working HEAD were independently checked by the coordinator.

## Fixed prerequisites

- Original official files at `tmp/c01-material/official/`, all hashes in frozen-inputs.json.
- Prior pinned source/runtime material at `tmp/verification-f03-three-implementations/`: SQAT v2.0 commit `94f489c053d1366da05d5e62838c3f54ac7715c3`, MoSQITo1.2.1 original/.22 sources and official C DLL variants. The prior original-C frontend-export DLL is `tmp/verification-f03-filter-independent/c022/reference.dll`.
- Prior delivery manifests and raw output hashes must verify before reuse. Reused outputs are referenced explicitly by design ID, path and original SHA-256; 24 B cells are reused, not newly executed. New sqrt inputs must match all 24 previous WAV-input arrays bitwise.
- Python environment: `tmp/acceptance-040-astra/fresh-venv/Scripts/python.exe`; package versions copied as prior-runtime provenance and freshly recorded in execution-audit.json. Analysis/plots also need scipy/openpyxl/matplotlib/Pillow. No replacement algorithms are installed.
- The dedicated GNU Octave8.4.0 container is `iso532-f03-octave-20261105`, originally built from Ubuntu24.04 image digest `ubuntu@sha256:fe81560990fae86dc4743202b2cb4d3df98d0bcf949173cecef15ce1127ef852`. This round creates `/matrix` **inside that container**. Its existing `/work` bind contains the prior pinned SQAT sources and is read only by the new harness. Source/output directories from the old round are never written. Preserve this runtime or recreate the exact package versions recorded in the previous round.

## Explicit interpreter selection

This run used two Python environments. `runtime-environments.json` records both executable hashes, versions and packages. The native audit venv has numpy/scipy/matplotlib/Pillow but **does not contain openpyxl**; therefore it must not run workbook extraction. Resolve `$analysisPython` once to an interpreter matching the recorded analysis environment (including openpyxl), and verify the recorded packages before running. If the default PATH resolves another environment, replace that variable with the explicit matching interpreter path. All commands below use the selected variables; no implicit interpreter switch is intended. The plotting environment is the recorded analysis environment.

## Freeze, shared levels and new Python/C calculations

```powershell
$delivery = 'docs/verification/2026-11-06-F03-factorial-matrix-118322f'
$auditPython = 'tmp/acceptance-040-astra/fresh-venv/Scripts/python.exe'
$analysisPython = (Get-Command python).Source
& $analysisPython "$delivery/freeze.py"
& $auditPython "$delivery/run_stationary.py"
& $auditPython "$delivery/run_tv.py" c 022
& $auditPython "$delivery/run_tv.py" c 024
& $auditPython "$delivery/run_tv.py" mos-round 022
& $auditPython "$delivery/run_tv.py" mos-round 024
& $auditPython "$delivery/run_tv.py" mos-noround 022
& $auditPython "$delivery/run_tv.py" mos-noround 024
& $analysisPython "$delivery/read_refs.py"
```

The frontend extension mechanically adds a post-filter RMS slice to original Mo source. `frontend-controls.json` requires exact native skip0 parity. The official C level API mutates caller input; the adapter makes a fresh independent copy for each call and byte-checks immutable shared levels afterward. The first preflight's rejected log is retained, and the complete A matrix was rerun after this harness fix. Do not remove or loosen these guards.

## Native SQAT in GNU Octave

Copy the original harness `run_sqat.m.txt` into scratch as `run_sqat.m`, then copy it, the generated `inputs/` directory and `stationary-levels.mat` into `/matrix` using `docker cp`. Start only the named dedicated container if it is stopped. Create `/matrix/inputs` and `/matrix/tv-outputs` there. Execute:

```text
docker exec iso532-f03-octave-20261105 octave-cli --no-gui --quiet /matrix/run_sqat.m 022
docker exec iso532-f03-octave-20261105 octave-cli --no-gui --quiet /matrix/run_sqat.m 024
docker exec -e OPENBLAS_NUM_THREADS=1 -e OMP_NUM_THREADS=1 iso532-f03-octave-20261105 octave-cli --no-gui --quiet /matrix/run_sqat.m 022 6 16
docker exec -e OPENBLAS_NUM_THREADS=1 -e OMP_NUM_THREADS=1 iso532-f03-octave-20261105 octave-cli --no-gui --quiet /matrix/run_sqat.m 022 15 25
docker exec -e OPENBLAS_NUM_THREADS=1 -e OMP_NUM_THREADS=1 iso532-f03-octave-20261105 octave-cli --no-gui --quiet /matrix/run_sqat.m 024 6 16
docker exec -e OPENBLAS_NUM_THREADS=1 -e OMP_NUM_THREADS=1 iso532-f03-octave-20261105 octave-cli --no-gui --quiet /matrix/run_sqat.m 024 15 25
```

Four disjoint TV jobs used the four available container CPUs; this is not a performance benchmark. Copy `/matrix/stationary-sqat022.mat`, `stationary-sqat024.mat` and the eight `/matrix/tv-outputs/*.mat` files into the corresponding **new** scratch paths. Preserve raw logs and exit codes. Stop this dedicated container after all workers exit; keep its files and original container for replay.

## Analysis, plot and delivery

```powershell
& $analysisPython "$delivery/analyze.py"
& $analysisPython "$delivery/coordinator_review.py"
& $analysisPython "$delivery/make_reports.py"
```

Expected design:328 cells = 304 new +24 reused; stationary264 result IDs and TV64 IDs match the design exactly. The separate all-20 TV reanalysis reads120 prior native files, including those24, so it is not added to the new-run count. For TV paired effects subtract matched arrays **before averaging** so insensitive pairs retain exact zero. Both original and adapted source hashes and original raw output hashes retain their literal meaning.

`full-walsh-decomposition.json` contains all16 four-factor or32 five-factor terms; reconstruction is checked at every cell. `paired-effects.json` contains signed main/DID effects, with explicit scaling relative to Walsh coefficients. `stationary-rankings.json` and `tv-rankings.json` rank N and Nprime separately. `all-tv-cancellation.json` uses fixed workbook coordinates; `all-tv-specific-cancellation.json` separates full-grid C022 reference and available workbook trajectories. Reported Mo timestamps are retained; physical indexing follows source decimation, while C/SQAT and workbook labels are directly checked.

Before delivery, run both repository redaction passes. SVG is not covered by the generic suffix list: inspect its XML text and metadata explicitly. PNG is binary: verify decoding, visually inspect labels and inspect textual metadata for identifying paths. Inspect the delivery diff, all UTF-8/unsupported files, and regenerate integrity hashes last. No complete third-party source, original WAV/workbook, DLL or large numeric archive belongs in this report directory.
