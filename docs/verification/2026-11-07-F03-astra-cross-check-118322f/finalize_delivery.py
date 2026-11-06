"""Assemble the cross-check delivery: copy text artefacts, CRLF -> LF, run tools/redact_paths.py and
--check, write delivery-check.md and delivery-integrity.json (SHA-256 after redaction, excluding itself).
Usage: finalize_delivery.py <delivery_dir>"""
import sys, shutil, pathlib, hashlib, json, subprocess

HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path("<REPO>")
OUT = pathlib.Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)

COPY = {
    "report.md": "report.md", "report.en.md": "report.en.md", "replay.md": "replay.md",
    "astra_residual.py": "astra_residual.py", "crosscheck.py": "crosscheck.py",
    "usl_main_effect_definition.py": "usl_main_effect_definition.py", "finalize_delivery.py": "finalize_delivery.py",
    "astra_residual.json": "astra_residual.json", "crosscheck.json": "crosscheck.json",
    "usl_main_effect_definition.json": "usl_main_effect_definition.json",
    "logs-astra_residual.log": "run-astra_residual.log", "logs-crosscheck.log": "run-crosscheck.log",
    "logs-usl_main_effect_definition.log": "run-usl_main_effect_definition.log",
    "levels2core/Cargo.toml": "levels2core.Cargo.toml.txt", "levels2core/Cargo.lock": "levels2core.Cargo.lock.txt",
    "levels2core/src/main.rs": "levels2core.main.rs.txt",
}
GENERATED = ("finalize_delivery.py", "delivery-check.md", "delivery-integrity.json", "redaction.log")


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def main():
    for src, dst in COPY.items():
        shutil.copyfile(HERE / src, OUT / dst)
    crlf = []
    for p in sorted(OUT.iterdir()):
        b = p.read_bytes()
        if b"\r\n" in b:
            p.write_bytes(b.replace(b"\r\n", b"\n")); crlf.append(p.name)
    tool = str(ROOT / "tools/redact_paths.py")
    r1 = subprocess.run([sys.executable, tool, str(OUT)], capture_output=True, text=True)
    r2 = subprocess.run([sys.executable, tool, "--check", str(OUT)], capture_output=True, text=True)
    open(OUT / "redaction.log", "w", encoding="utf-8", newline="\n").write(
        "$ redact_paths.py <folder>\n" + r1.stdout + r1.stderr + "\n$ redact_paths.py --check <folder>\n" + r2.stdout + r2.stderr)
    subprocess.run([sys.executable, tool, str(OUT)], capture_output=True, text=True)
    r3 = subprocess.run([sys.executable, tool, "--check", str(OUT)], capture_output=True, text=True)
    bad = []
    for p in sorted(OUT.iterdir()):
        b = p.read_bytes()
        try:
            b.decode("utf-8")
        except UnicodeDecodeError:
            bad.append(p.name)
        if b"\x00" in b:
            bad.append(p.name + " (NUL)")
    hits = []
    for p in sorted(OUT.iterdir()):
        if p.name in GENERATED:  # generated here / hold the search strings
            continue
        t = p.read_text(encoding="utf-8", errors="replace").lower()
        for needle in ("cclin", "users\\", "users/", "appdata", "<REPO>", "<REPO>"):
            if needle in t:
                hits.append(f"{p.name}: {needle}")
    check = ["# Delivery check", "", "Own delivery of the main agent (Claude Opus 5.5), same rules as the auditor's deliveries.", "",
             f"- Redaction: first pass output and `--check` are in `redaction.log`; final `--check` after the log was written: `{r3.stdout.strip()}`{(' / stderr: ' + r3.stderr.strip()) if r3.stderr.strip() else ''}.",
             f"- Manual search (case-insensitive) for the user name, user-profile folders and repository paths in any spelling: {'nothing found' if not hits else '; '.join(hits)}.",
             f"- Formats: `.md`, `.json`, `.py`, `.txt`, `.log` only (Rust sources and Cargo files delivered as `.txt`), all covered by the tool. UTF-8 / NUL problems: {'none' if not bad else ', '.join(bad)}.",
             f"- Line endings: {len(crlf)} files had CRLF and were converted to LF before the manifest was computed{': ' + ', '.join(crlf) if crlf else ''}.",
             "- Not delivered: the harness build, the Claude factor-attribution cell outputs (hashes in that round's `raw-output-hashes.json`), the workbooks. Astra's files are read in place from their tracked folders and are not copied.",
             "- `delivery-integrity.json` lists the SHA-256 of every other file after redaction and line-ending conversion, excluding itself.", ""]
    open(OUT / "delivery-check.md", "w", encoding="utf-8", newline="\n").write("\n".join(check))
    subprocess.run([sys.executable, tool, str(OUT)], capture_output=True, text=True)
    files = [{"path": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in sorted(OUT.iterdir()) if p.name != "delivery-integrity.json"]
    json.dump({"scope": "post-redaction UTF-8 delivery files (LF)", "excluded": ["delivery-integrity.json"], "file_count": len(files), "files": files},
              open(OUT / "delivery-integrity.json", "w", newline="\n"), indent=1)
    print("delivered", len(files) + 1, "files; crlf:", crlf, "; bad:", bad, "; hits:", hits, "; check:", r3.stdout.strip())


if __name__ == "__main__":
    main()
