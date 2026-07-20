# Contributing to ISO532

Thank you for helping improve ISO532. Contributions are especially useful when
they include a reproducible fixture, the calibration and field assumptions, and
the exact command used to obtain a result.

By participating, you agree to follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
Security-sensitive reports should follow [SECURITY.md](SECURITY.md), not a
public issue.

## Scope and contracts

- The engine accepts calibrated acoustic pressure in pascals at exactly 48 kHz.
- Keep MoSQITo parity evidence separate from ISO Annex B acceptance evidence.
- Treat golden hashes and scalar/SIMD/thread-count parity as compatibility
  contracts. Do not update fixtures or loosen tolerances merely to make a test
  pass.
- Keep the existing Rust, C ABI v1, and Python layouts stable unless the change
  explicitly proposes a versioned contract change.
- Do not commit ISO publications, local source archives, generated `data/`,
  credentials, or machine-specific paths.

## Development setup

Install a stable Rust toolchain and Python 3.9 or newer. Python 3.11 is the
documented local golden-generation environment. From the repository root:

```powershell
cargo build --workspace
cargo test
cargo fmt --check
cargo clippy --all-targets -- -D warnings
```

The Python extension and tests require a local virtual environment:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install maturin numpy pytest
.venv\Scripts\maturin.exe develop --release -m iso532-py\Cargo.toml
$env:ISO532_REQUIRE_PARITY='1'
.venv\Scripts\python.exe -m pytest iso532-py\tests -q
Remove-Item Env:ISO532_REQUIRE_PARITY
```

See [docs/GOLDEN-REGEN-SOP.md](docs/GOLDEN-REGEN-SOP.md) before running or
regenerating reference fixtures. Verify an existing local fixture set with:

```powershell
.venv\Scripts\python.exe tools\golden_manifest.py --verify
```

## Change workflow

1. Open an issue for contract changes, numerical changes, or significant API
   additions before implementation.
2. Add a failing test that demonstrates the intended behavior or defect.
3. Make the smallest implementation change that satisfies it.
4. Run the focused test, then the full correctness gates above.
5. Document user-visible changes under `Unreleased` in
   [CHANGELOG.md](CHANGELOG.md).

When numerical behavior could change, also run the bitwise hash dump and compare
all four recorded lines exactly:

```powershell
cargo test -p iso532 --test golden_zwtv dump_zwtv_output_hashes -- --ignored --nocapture
```

## Benchmarks

Only report benchmark results after correctness gates pass. Record CPU, OS,
toolchain, Rayon thread count, commit, command, median, and comparison baseline.
Run Criterion benchmarks individually and do not mix one-thread and multi-thread
history without clearly labeling it.

## Pull requests

Keep pull requests focused. Describe the behavior change, test evidence,
numerical-contract impact, and any verification that could not be run. Generated
C headers must be regenerated from the Rust ABI source rather than edited by
hand.
