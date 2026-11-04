# Recovery commands used after the initial fresh-environment failures.
# Run from the repository root; this modifies only the isolated verification venv.
$env:PIP_NO_INDEX = '0'
& tmp/acceptance-040-astra/fresh-venv/Scripts/python.exe -m pip install numpy==2.4.6 mosqito==1.2.1 pytest==9.1.1 maturin==1.14.1
& tmp/acceptance-040-astra/fresh-venv/Scripts/python.exe -m pip install matplotlib==3.11.2
python docs/verification/2026-11-04-release-0.4.0-fca4ccd/gates/run_python.py
# run_python_tests.py is the recorded collection-error recovery, without rebuilding.
# On a clean replay with matplotlib already present, run_python.py completes all steps.
