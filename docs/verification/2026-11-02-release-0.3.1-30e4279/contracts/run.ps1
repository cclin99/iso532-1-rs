# Run from repository root, frozen source already archived by parent runner.
$ErrorActionPreference='Stop'
$delivery=$PSScriptRoot
$env:CARGO_BUILD_JOBS='2'
tmp/acceptance-031/venv/Scripts/python.exe "$delivery/prepare-sig3.py"
if($LASTEXITCODE){throw 'sig3 preparation failed'}
cargo run --offline --locked --release --manifest-path "$delivery/rust/Cargo.toml" --target-dir tmp/acceptance-031/contract-target -- tmp/acceptance-031/source > "$delivery/rust-results.jsonl" 2> "$delivery/rust-build.log"
if($LASTEXITCODE){throw 'Rust harness failed'}
cargo build --offline --locked --release --manifest-path tmp/acceptance-031/source/Cargo.toml -p iso532-ffi --target-dir tmp/acceptance-031/contract-target > "$delivery/ffi-build.log" 2>&1
if($LASTEXITCODE){throw 'FFI build failed'}
cmd /c "$delivery/run-c.cmd" > "$delivery/c-build.log" 2>&1
if($LASTEXITCODE){throw 'C harness failed'}
tmp/acceptance-031/venv/Scripts/python.exe "$delivery/python-client.py" "$delivery/python-results.json"
if($LASTEXITCODE){throw 'Python harness failed'}
tmp/acceptance-031/venv/Scripts/python.exe "$delivery/summarize.py"
if($LASTEXITCODE){throw 'Contract summary failed'}
