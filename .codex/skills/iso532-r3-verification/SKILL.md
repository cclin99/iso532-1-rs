---
name: iso532-r3-verification
description: Verify ISO532 R3 review fixes across the Rust core, C ABI/header, Python binding, golden regeneration chain, and cross-language bitwise contract. Use after changing framing, error/field mappings, FFI exports, cbindgen output, PyO3 GIL handling, golden tools, or shared hash fixtures.
---

# ISO532 R3 Verification

Preserve numerical and ABI contracts while validating R3 changes. Run from the stated crate directory and stop at the first contract drift.

## Workflow

1. Inspect `git status --short`; preserve unrelated and untracked user files.
2. For behavior changes, demonstrate a focused RED test before implementation and rerun it GREEN afterward.
3. Verify core correctness from `iso532/`:

```powershell
cargo test
cargo test --test golden_zwtv dump_zwtv_output_hashes -- --ignored --nocapture
cargo test --test py_contract_dump -- --ignored --nocapture
cargo fmt --check
cargo clippy --all-targets -- -D warnings
```

Require the four R1 hashes documented by `iso532-rust-verification` and this Python contract exactly:

```text
py-contract: n=0x44e6822074554786 time=0xf076bcb342595537 frames=500
```

4. Verify the FFI from `iso532-ffi/`:

```powershell
cargo test --features test-panic
cbindgen --config cbindgen.toml --crate iso532-ffi --output include/iso532.h
git diff --exit-code include/iso532.h
cargo fmt --check
cargo clippy --all-targets --all-features -- -D warnings
```

Require cbindgen 0.29.4; install with `cargo install cbindgen --version 0.29.4 --locked` when unavailable. Regenerate the header; never hand-edit it. Inspect the diff before accepting it. Run the platform C smoke test when the compiler environment is available.

5. Verify Python from `iso532-py/`:

```powershell
..\.venv\Scripts\python.exe -m maturin develop --release
..\.venv\Scripts\python.exe -m pytest tests/test_smoke.py -v
..\.venv\Scripts\python.exe -m pytest tests/ --collect-only -q
$env:ISO532_REQUIRE_PARITY = "1"
..\.venv\Scripts\python.exe -m pytest tests/test_parity_mosqito.py -v
```

Treat the smoke bitwise test as mandatory. Set `ISO532_REQUIRE_PARITY=1` for formal parity; missing dependencies must fail rather than skip, and require 18 passed with zero skipped. Collection must not error when optional parity dependencies are absent.

6. Verify the golden chain from the repository root:

```powershell
bash -n tools/setup_env.sh
.venv\Scripts\python.exe tools/golden_manifest.py --verify
```

Run `bash tools/setup_env.sh` when environment recreation is authorized. If the project venv is locked, validate twice in a clean isolated copy and record that deviation; do not delete or overwrite the user's venv.

7. Run final `cargo fmt --check`, clippy, test, Python, header regeneration, and `git diff --check` gates after all phases converge. Do not benchmark until correctness and hashes are clean.

## Failure Rules

- Any frozen hash change is a bug unless numerical behavior was explicitly requested.
- Any generated header diff after regeneration means the committed header is stale.
- Distinguish source failures from Windows file locks, ACLs, or sandbox failures; retry with scoped elevation rather than changing code.
- Record commands, counts, hashes, skipped platform-only checks, environmental deviations, and CI work that cannot be observed locally.
