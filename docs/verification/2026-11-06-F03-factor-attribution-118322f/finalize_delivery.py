"""Assemble the delivery folder: copy text artefacts (scripts as .txt where needed), hash the raw
binaries that stay out of the repository, convert CRLF -> LF, run tools/redact_paths.py and --check,
write delivery-check.md (template; the numbers are filled from the tool output) and
delivery-integrity.json (SHA-256 of every delivered file after redaction, excluding itself).
Usage: finalize_delivery.py <delivery_dir>"""
import sys, shutil, pathlib, hashlib, json, subprocess

HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path("<REPO>")
OUT = pathlib.Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)

COPY = {
    "preregistration.md": "preregistration.md", "preregistration.zh-TW.md": "preregistration.zh-TW.md",
    "report.md": "report.md", "report.en.md": "report.en.md", "replay.md": "replay.md",
    "results.json": "results.json", "calibration.json": "calibration.json",
    "slopes_port.py": "slopes_port.py", "refs.py": "refs.py", "run_factorial.py": "run_factorial.py", "analyze.py": "analyze.py", "validate.py": "validate.py",
    "finalize_delivery.py": "finalize_delivery.py",
    "harness/Cargo.toml": "harness.Cargo.toml.txt", "harness/Cargo.lock": "harness.Cargo.lock.txt", "harness/src/main.rs": "harness.main.rs.txt",
    "sqat/run_sqat_variant.m": "run_sqat_variant.m.txt", "sqat/eps0-022.diff": "sqat-eps0-022.diff.txt", "sqat/eps0-024.diff": "sqat-eps0-024.diff.txt",
    "logs/factorial.log": "run-factorial.log", "logs/sqat_e0_0.24.log": "run-sqat-e0-024.log", "logs/sqat_e0_0.22.log": "run-sqat-e0-022.log",
    "logs/validate.log": "validate.log", "logs/analyze.log": "analyze.log",
}


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def main():
    for src, dst in COPY.items():
        s = HERE / src
        if s.exists():
            shutil.copyfile(s, OUT / dst)
        else:
            print("missing", src)
    # raw outputs (not delivered): hashes
    raw = {"note": "binary outputs stay out of the repository; SHA-256 of the files as produced (not redacted)", "files": {}}
    for d in ("out/rust", "out/fact", "out/sqat"):
        for p in sorted((HERE / d).glob("*")):
            if p.is_file():
                raw["files"][f"{d}/{p.name}"] = {"bytes": p.stat().st_size, "sha256": sha(p)}
    for p in sorted((ROOT / "tmp/impl-2026-11-05/out").glob("*")):
        raw["files"][f"2026-11-05/out/{p.name}"] = {"bytes": p.stat().st_size, "sha256": sha(p)}
    for v in ("022", "024"):
        for s in range(1, 26):
            for f in ("Loudness.csv", "SpecLoudness.csv"):
                p = ROOT / f"tmp/usl-2026-11-05/cli-v{v}/sig{s}/{f}"
                if p.exists():
                    raw["files"][f"official-cli-v{v}/sig{s}/{f}"] = {"bytes": p.stat().st_size, "sha256": sha(p)}
    for name in ("sqat/var-e0-022/Loudness_ISO532_1.m", "sqat/var-e0-024/Loudness_ISO532_1.m"):
        raw["files"][name] = {"bytes": (HERE / name).stat().st_size, "sha256": sha(HERE / name), "note": "GPL-3.0 source, not delivered; diff delivered"}
    for name in ("var-022", "var-024"):
        p = ROOT / f"tmp/sqat-claude-2026-11-06/{name}/Loudness_ISO532_1.m"
        raw["files"][f"2026-11-05/{name}/Loudness_ISO532_1.m"] = {"bytes": p.stat().st_size, "sha256": sha(p)}
    json.dump(raw, open(OUT / "raw-output-hashes.json", "w", newline="\n"), indent=1)
    # CRLF -> LF
    crlf = []
    for p in sorted(OUT.iterdir()):
        b = p.read_bytes()
        if b"\r\n" in b:
            p.write_bytes(b.replace(b"\r\n", b"\n")); crlf.append(p.name)
    # redaction
    r1 = subprocess.run([sys.executable, str(ROOT / "tools/redact_paths.py"), str(OUT)], capture_output=True, text=True)
    r2 = subprocess.run([sys.executable, str(ROOT / "tools/redact_paths.py"), "--check", str(OUT)], capture_output=True, text=True)
    open(OUT / "redaction.log", "w", encoding="utf-8", newline="\n").write("$ redact_paths.py <folder>\n" + r1.stdout + r1.stderr + "\n$ redact_paths.py --check <folder>\n" + r2.stdout + r2.stderr)
    # second pass so that redaction.log itself is covered
    subprocess.run([sys.executable, str(ROOT / "tools/redact_paths.py"), str(OUT)], capture_output=True, text=True)
    r3 = subprocess.run([sys.executable, str(ROOT / "tools/redact_paths.py"), "--check", str(OUT)], capture_output=True, text=True)
    # non-UTF-8 / NUL check
    bad = []
    for p in sorted(OUT.iterdir()):
        b = p.read_bytes()
        try:
            b.decode("utf-8")
        except UnicodeDecodeError:
            bad.append(p.name)
        if b"\x00" in b:
            bad.append(p.name + " (NUL)")
    # manual grep for identifying strings
    hits = []
    for p in sorted(OUT.iterdir()):
        if p.name in ("finalize_delivery.py", "delivery-check.md", "delivery-integrity.json", "redaction.log"):  # generated here / hold the needle strings
            continue
        t = p.read_text(encoding="utf-8", errors="replace").lower()
        for needle in ("cclin", "users\\", "users/", "appdata", "<REPO>", "<REPO>"):
            if needle in t:
                hits.append(f"{p.name}: {needle}")
    check = ["# Delivery check", "", "Own delivery of the main agent (Claude Fable 5.1), same rules as the auditor's deliveries.", "",
             f"- Redaction: first pass output and `--check` are in `redaction.log`; final `--check` after the log was written: `{r3.stdout.strip()}`{(' / stderr: ' + r3.stderr.strip()) if r3.stderr.strip() else ''}.",
             f"- Manual search (case-insensitive) for the user name, user-profile folders and repository paths in any spelling: {'nothing found' if not hits else '; '.join(hits)}.",
             f"- Formats: `.md`, `.json`, `.py`, `.txt`, `.log` only (Rust, MATLAB/Octave and diff sources delivered as `.txt`), all covered by the tool. UTF-8 / NUL problems: {'none' if not bad else ', '.join(bad)}.",
             f"- Line endings: {len(crlf)} files had CRLF and were converted to LF before the manifest was computed: {', '.join(f'`{c}`' for c in crlf) if crlf else 'none'}.",
             "- Not delivered: stage dumps, factorial cell outputs, Octave outputs, the official CLI outputs, WAV-derived inputs, the official sources and workbooks, the SQAT source (GPL-3.0; only the one-line diffs are delivered). Their SHA-256 are in `raw-output-hashes.json` (unredacted binaries; these hashes keep their original meaning).",
             "- `delivery-integrity.json` lists the SHA-256 of every other file after redaction and line-ending conversion, excluding itself.", ""]
    open(OUT / "delivery-check.md", "w", encoding="utf-8", newline="\n").write("\n".join(check))
    subprocess.run([sys.executable, str(ROOT / "tools/redact_paths.py"), str(OUT)], capture_output=True, text=True)
    files = [{"path": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in sorted(OUT.iterdir()) if p.name != "delivery-integrity.json"]
    json.dump({"scope": "post-redaction UTF-8 delivery files (LF)", "excluded": ["delivery-integrity.json"], "file_count": len(files), "files": files},
              open(OUT / "delivery-integrity.json", "w", newline="\n"), indent=1)
    print("delivered", len(files) + 1, "files; crlf:", crlf, "; bad:", bad, "; hits:", hits, "; check:", r3.stdout.strip())


if __name__ == "__main__":
    main()
