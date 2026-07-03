#!/usr/bin/env bash
# Creates .venv, installs mosqito 1.2.1 from local tarball, fetches ISO Annex B test data.
set -euo pipefail
cd "$(dirname "$0")/.."

if command -v python >/dev/null 2>&1; then
  PY_BOOT=python
elif command -v python.exe >/dev/null 2>&1; then
  PY_BOOT=python.exe
elif command -v py >/dev/null 2>&1; then
  PY_BOOT="py -3"
else
  echo "python not found" >&2
  exit 1
fi
$PY_BOOT -m venv .venv
if [ -x .venv/Scripts/python.exe ]; then
  PY=.venv/Scripts/python.exe
elif [ -x .venv/Scripts/python ]; then
  PY=.venv/Scripts/python
elif [ -x .venv/bin/python ]; then
  PY=.venv/bin/python
else
  echo "venv python not found" >&2
  exit 1
fi
$PY -m pip install --quiet --upgrade pip
$PY -m pip install --quiet ./mosqito-1.2.1.tar.gz openpyxl matplotlib
$PY -c "import mosqito, scipy, numpy; print('mosqito OK, scipy', scipy.__version__, 'numpy', numpy.__version__)"

# Annex B test data from the MoSQITo repo (not shipped in the sdist)
mkdir -p data
if [ ! -d data/annexb ]; then
  git clone --depth 1 --branch v1.2.1 https://github.com/Eomys/MoSQITo /tmp/mosqito-repo \
    || git clone --depth 1 https://github.com/Eomys/MoSQITo /tmp/mosqito-repo
  mkdir -p data/annexb
  cp /tmp/mosqito-repo/tests/input/*.wav data/annexb/
  cp /tmp/mosqito-repo/tests/input/*.csv data/annexb/
  cp /tmp/mosqito-repo/tests/input/*.xlsx data/annexb/ 2>/dev/null || true
  rm -rf /tmp/mosqito-repo
fi
ls data/annexb