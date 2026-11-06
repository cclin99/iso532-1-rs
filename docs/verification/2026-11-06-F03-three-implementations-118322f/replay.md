# Replay — native three-implementation coefficient experiment

Run from the repository root. Delivery is this directory; bulk scratch data is `tmp/verification-f03-three-implementations/`. The original preregistration began on 2026-11-05; the completed delivery moved to the 2026-11-06 directory after all writers closed. The original timestamps and frozen preregistration hash remain unchanged.

## Prerequisites and fixed inputs

1. Restore the original official Annex A C files, Annex B WAV/text/workbooks under `tmp/c01-material/official/`. Verify **every** raw-input hash against `frozen-inputs.json`. Do not substitute rounded CSV output or regenerated goldens for the original references.
2. Python 3.11, packages recorded in `python-runtime.json`; MoSQITo **1.2.1** source was read from `tmp/acceptance-040-astra/fresh-venv/Lib/site-packages/mosqito`. The numerical worker uses that environment's Python; preparation/analysis also need numpy, scipy and openpyxl. Source hashes are stronger identification than a version string alone.
3. MSVC 2022 BuildTools, `vcvars64.bat` at its default Program Files (x86) path. Build commands are retained as `.cmd.txt`. `/O2 /fp:precise` builds a DLL from the unmodified official C included in `core-wrapper.c.txt`. The wrapper only calls original stages and exports APIs. Counterfactual changes exactly one ASCII digit in the official coefficient table.
4. Download the four SQAT `.m` files from the commit-pinned URLs in `sqat-acquisition.json` into scratch `sqat-v2.0/`, preserving the listed relative paths. Verify their SHA-256 and Git-blob SHA-1. Do not use moving main or latest URLs. Commit: `94f489c053d1366da05d5e62838c3f54ac7715c3` (v2.0).
5. Native runtime was GNU Octave **8.4.0**, Ubuntu 24.04 base image digest `ubuntu@sha256:fe81560990fae86dc4743202b2cb4d3df98d0bcf949173cecef15ce1127ef852`. Installed package versions are retained in `octave-package-versions.txt`; only `signal` was loaded by the harness, not `statistics`. Mount **only this scratch directory** as `/work` in a dedicated container. The original container name was `iso532-f03-octave-20261105`. MATLAB R2021a was unavailable due to an expired license; the MATLAB log is not a numerical result.

## Preparation and native execution

The following uses `$delivery` only as a task-specific path variable. Update it if replaying elsewhere.

```powershell
$delivery = 'docs/verification/2026-11-06-F03-three-implementations-118322f'
python "$delivery/prepare.py"
python "$delivery/prepare_sqat.py"
python "$delivery/native_run.py" c 022
python "$delivery/native_run.py" c 024
tmp/acceptance-040-astra/fresh-venv/Scripts/python.exe "$delivery/native_run.py" mos 022
tmp/acceptance-040-astra/fresh-venv/Scripts/python.exe "$delivery/native_run.py" mos 024
tmp/acceptance-040-astra/fresh-venv/Scripts/python.exe "$delivery/common_stage.py"
docker exec -e OPENBLAS_NUM_THREADS=1 -e OMP_NUM_THREADS=1 iso532-f03-octave-20261105 octave-cli --no-gui --quiet /work/run_sqat.m 024
docker exec -e OPENBLAS_NUM_THREADS=1 -e OMP_NUM_THREADS=1 iso532-f03-octave-20261105 octave-cli --no-gui --quiet /work/run_sqat.m 022
```

Each SQAT signal is saved separately. The optional arguments after the variant select disjoint signals, e.g. `... /work/run_sqat.m 024 14 18 24 7 10 12 16 19 21`. Existing completed outputs are skipped, so use a new clean scratch directory or manually confirm their hashes before a replay; do not accidentally mix runs. This round used two initial workers for signals 1–6 and 9, then intentionally stopped them and ran four disjoint shards on a four-CPU container. All four shards completed with exit 0. Their logs include signal durations. This is numerical verification, not a performance benchmark.

The original common-stage invocation was also run separately while the long jobs continued:

```text
cd('/work'); a=load('common-core.mat');
[n024,ns024]=sqat_slope_024(a.core');
[n022,ns022]=sqat_slope_022(a.core');
save('-mat7-binary','sqat-common-slope.mat','n024','ns024','n022','ns022');
```

`prepare_sqat.py` extracts an exact source-body span into these native `.m` wrappers, without editing the algorithm. Source/body/wrapper hashes are in `sqat-freeze.json`. The original third-party source and extracted body remain in tmp rather than being republished in this delivery.

## Analysis and checks

```powershell
python "$delivery/analyze.py"
python "$delivery/numeric_controls.py"
python "$delivery/make_reports.py"
```

`numeric_controls.py` also freshly evaluates the same 25 inputs through the prior original-C DLL at `tmp/verification-f03-filter-independent/c022/reference.dll` and requires bitwise equality with this round's C022 outputs. Its binary hash is recorded; it reuses the binary, **not prior numeric output**. This is an additional wrapper/export check, not the primary reference or a substitute for native MoSQITo/SQAT.

Expected coverage is six output directories × 25 readable finite arrays. The signal 1 MoSQITo route uses native private main-loudness and slope stages; signals 2–25 use its original public APIs. Preserve original returned time vectors. `analyze.py` documents the source-index interpretation of MoSQITo's linspace time labels in `alignment-deviation.md`, retains exact physical 2-ms matching and reports extra tails; it never fits or interpolates results.

Before checking in delivery, run the project's path redactor and its check mode, inspect unsupported/non-UTF-8 formats and the delivery diff, and regenerate the delivery integrity manifest **after** any transformation. Raw input/source/binary/output hashes always refer to the original local files; they are not hashes of redacted logs. Do not include third-party raw files or numeric archives in the repository delivery.
