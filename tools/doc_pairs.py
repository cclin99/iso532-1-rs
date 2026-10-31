#!/usr/bin/env python3
"""Check the English / Traditional-Chinese document pairs under docs/.

Policy: docs/DOCUMENTATION-LANGUAGE-POLICY.md section 2 and 8.

    python tools/doc_pairs.py --check   # exit 1 on any error, prints "ok" otherwise
    python tools/doc_pairs.py --list    # table of every docs/*.md with pair status

A paired document is `NAME.md` (English) plus `NAME.zh-TW.md` (Chinese). Both must
start with a pair line right after the H1 title:

    > 對照／Pair: [中文版](NAME.zh-TW.md) · source: en · synced 2026-11-01
    > 對照／Pair: [English](NAME.md) · 來源：en · 同步 2026-11-01

The link target must name the counterpart, `source`/`來源` must agree, and the
synced dates must be equal. Files in EXEMPT are verification evidence or
ecosystem files and are not paired; files in BACKLOG may be unpaired for now and
are reported as warnings, not errors.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / "docs"

# Verification deliveries and other files that are never paired (policy §3).
EXEMPT = {
    "修正報告.md",
    "修正報告2.md",
    "修正後獨立驗證報告.md",
}

# Allowed to be unpaired for now; listed in docs/README.md with a priority.
BACKLOG = {
    "ARCHITECTURE-PERFORMANCE-RISK-REPORT-2026-07-10.md",
    "R3-FIXES-REVIEW-2026-07-11.md",
    "R3-REVIEW-2026-07-11.md",
    "R3-REVIEW-FIXES-IMPLEMENTATION-2026-07-11.md",
    "R4-REVIEW-CLOSEOUT-2026-07-10.md",
    "R5-REVIEW-2-FIXES-2026-07-17.md",
    "R5-REVIEW-3-FIXES-2026-07-18.md",
    "R5-REVIEW-FIXES-2026-07-17.md",
    "R5-REVIEW-FIXES-IMPLEMENTATION-2026-07-17.md",
    "iso532-1-rs-code-review-remediation.md",
}

PAIR_RE = re.compile(
    r"^> 對照／Pair: \[[^\]]+\]\(([^)]+)\) · (?:source|來源)[:：]\s*(en|zh) · (?:synced|同步) (\d{4}-\d{2}-\d{2})\s*$"
)


def pair_line(path: Path):
    """Return (target, source, date) from the first 5 lines, or None."""
    try:
        head = path.read_text(encoding="utf-8").splitlines()[:5]
    except UnicodeDecodeError:
        return None
    for line in head:
        m = PAIR_RE.match(line.strip())
        if m:
            return m.group(1), m.group(2), m.group(3)
    return None


def main(argv: list[str]) -> int:
    mode = "--check"
    if argv[1:]:
        mode = argv[1]
    if mode not in ("--check", "--list"):
        print(__doc__)
        return 2

    files = sorted(p.name for p in DOCS.glob("*.md"))
    errors: list[str] = []
    warnings: list[str] = []
    rows: list[tuple[str, str, str]] = []

    for name in files:
        if name in EXEMPT:
            rows.append((name, "exempt", "-"))
            continue
        if name.endswith(".zh-TW.md"):
            base = name[: -len(".zh-TW.md")] + ".md"
            if base not in files:
                errors.append(f"{name}: Chinese file without English counterpart {base}")
            continue  # the English side reports the pair
        zh = name[:-3] + ".zh-TW.md"
        if zh not in files:
            if name in BACKLOG:
                warnings.append(f"{name}: unpaired (backlog)")
                rows.append((name, "backlog", "-"))
            else:
                errors.append(f"{name}: missing {zh}")
                rows.append((name, "MISSING zh", "-"))
            continue
        en_pl = pair_line(DOCS / name)
        zh_pl = pair_line(DOCS / zh)
        status = "paired"
        date = "-"
        if en_pl is None:
            errors.append(f"{name}: no pair line")
            status = "no pair line"
        if zh_pl is None:
            errors.append(f"{zh}: no pair line")
            status = "no pair line"
        if en_pl and zh_pl:
            if Path(en_pl[0]).name != zh:
                errors.append(f"{name}: pair line points to {en_pl[0]}, expected {zh}")
            if Path(zh_pl[0]).name != name:
                errors.append(f"{zh}: pair line points to {zh_pl[0]}, expected {name}")
            if en_pl[1] != zh_pl[1]:
                errors.append(f"{name}/{zh}: source disagrees ({en_pl[1]} vs {zh_pl[1]})")
            if en_pl[2] != zh_pl[2]:
                errors.append(f"{name}/{zh}: synced dates differ ({en_pl[2]} vs {zh_pl[2]})")
                status = "out of sync"
            date = en_pl[2]
        rows.append((name, status, date))

    if mode == "--list":
        width = max(len(r[0]) for r in rows) if rows else 10
        for name, status, date in rows:
            print(f"{name:<{width}}  {status:<12}  {date}")

    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"error: {e}")
    if errors:
        print(f"{len(errors)} error(s)")
        return 1
    if mode == "--check":
        print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
