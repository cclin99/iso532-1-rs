"""Shared test bootstrap: tools/ on sys.path + parity enforcement switch."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

REQUIRE_PARITY = os.environ.get("ISO532_REQUIRE_PARITY") == "1"
