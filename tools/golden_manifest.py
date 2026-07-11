"""Generate/verify a SHA256 manifest for data/golden and data/annexb.

PER-ENVIRONMENT contract: golden bytes depend on the libm of the machine
that generated them (see docs/CI-HASH-GATE-DEBUG-2026-07-10.md). The
manifest answers exactly one question: "does regeneration on THIS machine
reproduce the data the Rust test suite was validated against?" On a new
machine a mismatch is EXPECTED: regenerate the manifest per the SOP
(docs/GOLDEN-REGEN-SOP.md) and re-run the golden tests.

Usage:
  python tools/golden_manifest.py --generate
  python tools/golden_manifest.py --verify
"""
import argparse
import hashlib
import platform
import sys
from pathlib import Path

if sys.version_info < (3, 11):
    sys.exit(
        "golden_manifest.py needs Python >= 3.11 (hashlib.file_digest); "
        "run it with the tools venv per docs/GOLDEN-REGEN-SOP.md"
    )

ROOT = Path(__file__).resolve().parent.parent
PATTERNS = ("golden/**/*.bin", "golden/**/meta.json", "annexb/*")


def collect(data_root: Path) -> dict[str, str]:
    files = set()
    for pattern in PATTERNS:
        files.update(p for p in data_root.glob(pattern) if p.is_file())
    entries = {}
    for p in sorted(files):
        with p.open("rb") as f:
            digest = hashlib.file_digest(f, "sha256").hexdigest()
        entries[p.relative_to(data_root).as_posix()] = digest
    return entries


def env_header() -> list[str]:
    try:
        import numpy
        import scipy

        vers = f"numpy {numpy.__version__}, scipy {scipy.__version__}"
    except ImportError:
        vers = "numpy/scipy not importable"
    return [
        "# PER-ENVIRONMENT manifest: only valid on the machine/env that generated it.",
        "# On a new machine, follow docs/GOLDEN-REGEN-SOP.md instead of trusting --verify.",
        f"# env: {platform.platform()} / {platform.machine()} / "
        f"python {platform.python_version()} / {vers}",
    ]


def generate(data_root: Path, manifest: Path) -> int:
    entries = collect(data_root)
    if not entries:
        print(f"error: no files matched under {data_root}", file=sys.stderr)
        return 1
    lines = env_header() + [f"{h}  {rel}" for rel, h in sorted(entries.items())]
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {manifest} ({len(entries)} files)")
    return 0


def verify(data_root: Path, manifest: Path) -> int:
    if not manifest.exists():
        print(f"error: manifest {manifest} missing", file=sys.stderr)
        return 1
    want = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        digest, rel = line.split(None, 1)
        want[rel] = digest
    got = collect(data_root)
    missing = sorted(set(want) - set(got))
    extra = sorted(set(got) - set(want))
    mismatch = sorted(rel for rel in set(want) & set(got) if want[rel] != got[rel])
    for rel in missing:
        print(f"MISSING   {rel}")
    for rel in extra:
        print(f"EXTRA     {rel}")
    for rel in mismatch:
        print(f"MISMATCH  {rel}")
    if missing or extra or mismatch:
        print(
            f"verify FAILED: {len(missing)} missing, {len(extra)} extra, "
            f"{len(mismatch)} mismatch (of {len(want)} manifest entries)"
        )
        return 1
    print(f"verify OK: {len(want)} files match")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--generate", action="store_true")
    mode.add_argument("--verify", action="store_true")
    ap.add_argument("--data-root", type=Path, default=ROOT / "data",
                    help="override for self-tests")
    ap.add_argument("--manifest", type=Path, default=ROOT / "tools" / "golden.sha256",
                    help="override for self-tests")
    args = ap.parse_args()
    if args.generate:
        return generate(args.data_root, args.manifest)
    return verify(args.data_root, args.manifest)


if __name__ == "__main__":
    sys.exit(main())
