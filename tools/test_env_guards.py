"""BDD regression tests for the golden-environment setup guards."""

import ast
import re
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
SETUP = (TOOLS / "setup_env.sh").read_text(encoding="utf-8")
LOCK = (TOOLS / "requirements.lock").read_text(encoding="utf-8")


class EnvironmentGuardBehavior(unittest.TestCase):
    def test_boot_python_is_checked_before_venv_creation(self):
        """Given PY_BOOT, when setup starts, then 3.11 is checked before venv creation."""
        create_at = SETUP.index('"${PY_BOOT[@]}" -m venv .venv')
        prefix = SETUP[:create_at]
        self.assertIn('"${PY_BOOT[@]}" - <<\'EOF\'', prefix)
        self.assertIn("sys.version_info[:2] != (3, 11)", prefix)

    def test_testkit_guard_survives_python_optimization(self):
        """Given python -O, when testkit loads, then its port guard is not an assert."""
        source = (TOOLS / "iso532_testkit.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        self.assertFalse(any(isinstance(node, ast.Assert) for node in ast.walk(tree)))
        self.assertIn('raise RuntimeError("fnv1a_f64 port drifted', source)

    def test_tarball_sha_has_one_source_in_lock_header(self):
        """Given a pinned tarball, when setup verifies it, then SHA comes from the lock."""
        lock_hashes = re.findall(
            r"^#\s+mosqito-1\.2\.1\.tar\.gz\s+sha256=([0-9a-f]{64})\s*$",
            LOCK,
            re.MULTILINE,
        )
        self.assertEqual(len(lock_hashes), 1)
        self.assertNotIn(lock_hashes[0], SETUP)
        self.assertIn('Path("tools/requirements.lock")', SETUP)
        self.assertIn("expected exactly one", SETUP)


if __name__ == "__main__":
    unittest.main()
