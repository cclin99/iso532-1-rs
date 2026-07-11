#!/usr/bin/env bash
# Creates .venv, installs mosqito 1.2.1 from local tarball, fetches ISO Annex B test data.
set -euo pipefail
cd "$(dirname "$0")/.."

if command -v python >/dev/null 2>&1; then
  PY_BOOT=(python)
elif command -v python.exe >/dev/null 2>&1; then
  PY_BOOT=(python.exe)
elif command -v py >/dev/null 2>&1; then
  PY_BOOT=(py -3)
else
  echo "python not found" >&2
  exit 1
fi
"${PY_BOOT[@]}" - <<'EOF'
import sys
if sys.version_info[:2] != (3, 11):
    sys.exit(
        f"golden chain requires Python 3.11 (got {sys.version.split()[0]}); "
        "refusing to create or modify .venv; see tools/requirements.lock header"
    )
EOF
"${PY_BOOT[@]}" -m venv .venv
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
$PY -m pip install --quiet -r tools/requirements.lock
$PY - <<'EOF'
import hashlib
import re
from pathlib import Path

lock_path = Path("tools/requirements.lock")
lock_text = lock_path.read_text(encoding="utf-8")
matches = re.findall(r"^#\s+mosqito-1\.2\.1\.tar\.gz\s+sha256=([0-9a-f]{64})\s*$", lock_text, re.MULTILINE)
if len(matches) != 1:
    raise SystemExit(
        f"expected exactly one '# mosqito-1.2.1.tar.gz sha256=<64 lowercase hex>' "
        f"entry in {lock_path}; found {len(matches)}"
    )
want = matches[0]
with open("mosqito-1.2.1.tar.gz", "rb") as f:
    got = hashlib.sha256(f.read()).hexdigest()
if got != want:
    raise SystemExit(f"mosqito tarball sha256 mismatch:\n  got  {got}\n  want {want}")
print("mosqito tarball sha256 OK")
EOF
$PY -m pip install --quiet --no-deps ./mosqito-1.2.1.tar.gz
$PY -c "import mosqito, scipy, numpy, openpyxl, pyuff; print('golden env OK, scipy', scipy.__version__, 'numpy', numpy.__version__)"

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
