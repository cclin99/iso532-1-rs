#!/usr/bin/env python3
"""Replace workstation-specific filesystem paths in text files with placeholders.

Audit and verification reports are written outside this repository and quote
command lines with absolute paths. Before they are committed, run this script
on the files (or directories) so that the placeholders below replace the
identifying prefixes. Backslash, JSON-escaped double-backslash and
forward-slash spellings are all handled. GitHub handles and URLs are not paths
and are left alone.

    python tools/redact_paths.py docs/修正報告.md docs/verification
    python tools/redact_paths.py --check docs            # exit 1 if anything is left

The placeholder vocabulary is fixed so that different rounds stay comparable:

    <AUDIT_PYTHON>  interpreter bundled with the auditor's tooling
    <AUDIT_HOME>    the auditor's working directory root
    <USER_HOME>     any other path under the auditor's user profile
    <REPO>          this repository's working copy
    <PANEL_REPO>    the iso532-rs-panel working copy
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Ordered: longer / more specific prefixes first. Patterns are regexes over a
# "normalised" path spelling where the separator is matched by SEP.
SEP = r"(?:\\\\|\\|/)"
RULES: list[tuple[str, str]] = [
    (
        rf"[A-Za-z]:{SEP}Users{SEP}[^\\/\s\"']+{SEP}\.cache{SEP}codex-runtimes{SEP}[^\\/\s\"']+{SEP}dependencies{SEP}python{SEP}python\.exe",
        "<AUDIT_PYTHON>",
    ),
    (rf"[A-Za-z]:{SEP}Users{SEP}[^\\/\s\"']+{SEP}Documents{SEP}Codex", "<AUDIT_HOME>"),
    (rf"[A-Za-z]:{SEP}Users{SEP}[^\\/\s\"']+", "<USER_HOME>"),
    (rf"/c/Users/[^/\s\"']+", "<USER_HOME>"),
    # repository paths are matched case-insensitively (shell output may print `d:\iso532`)
    (rf"(?i)[A-Za-z]:{SEP}iso532-rs-panel", "<PANEL_REPO>"),
    (rf"(?i)[A-Za-z]:{SEP}iso532-panel", "<PANEL_REPO>"),
    (rf"(?i)[A-Za-z]:{SEP}ISO532(?![\w-])", "<REPO>"),
    # Git Bash / MSYS drive spelling (`/d/ISO532`), as printed by shell scripts
    (r"(?i)(?<![\w.-])/[a-z]/iso532-rs-panel(?![\w-])", "<PANEL_REPO>"),
    (r"(?i)(?<![\w.-])/[a-z]/iso532-panel(?![\w-])", "<PANEL_REPO>"),
    (r"(?i)(?<![\w.-])/[a-z]/ISO532(?![\w-])", "<REPO>"),
]
COMPILED = [(re.compile(p), r) for p, r in RULES]
TEXT_SUFFIXES = {".md", ".json", ".txt", ".log", ".ps1", ".py", ".csv", ".yml", ".yaml", ".toml", ".sh"}
# build products and vendored trees are never committed; skip them when a directory is given
SKIP_DIRS = {"target", ".venv", ".git", "node_modules", "mosqito-1.2.1", "__pycache__"}


def redact_text(text: str) -> tuple[str, int]:
    count = 0
    for pattern, repl in COMPILED:
        text, n = pattern.subn(repl, text)
        count += n
    return text, count


def iter_files(paths: list[str]):
    for p in paths:
        path = Path(p)
        if path.is_dir():
            for f in sorted(path.rglob("*")):
                if SKIP_DIRS.intersection(f.relative_to(path).parts[:-1]):
                    continue
                if f.is_file() and f.suffix.lower() in TEXT_SUFFIXES:
                    yield f
        elif path.is_file():
            yield path
        else:
            sys.exit(f"not found: {path}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--check", action="store_true", help="report remaining identifying paths, change nothing")
    args = ap.parse_args()

    remaining = 0
    changed = 0
    for f in iter_files(args.paths):
        try:
            text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            print(f"{f}: not UTF-8, skipped (inspect manually)", file=sys.stderr)
            continue
        new, n = redact_text(text)
        if n == 0:
            continue
        if args.check:
            remaining += n
            print(f"{f}: {n} identifying path(s) remain")
        else:
            f.write_text(new, encoding="utf-8", newline="")
            changed += 1
            print(f"{f}: {n} replaced")
    if args.check:
        print("clean" if remaining == 0 else f"{remaining} identifying path(s) remain")
        return 1 if remaining else 0
    print(f"{changed} file(s) changed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
