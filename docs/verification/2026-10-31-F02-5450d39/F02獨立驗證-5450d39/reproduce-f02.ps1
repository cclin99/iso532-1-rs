param(
 [Parameter(Mandatory=$true)][string]$RunDirectory,
 [string]$Repo='<REPO>',
 [string]$Python='<AUDIT_PYTHON>',
 [string]$BindingPython='<REPO>\.venv\Scripts\python.exe'
)
$ErrorActionPreference='Stop'
$bundle=$PSScriptRoot
if(Test-Path -LiteralPath $RunDirectory){throw 'Use a new run directory.'}
New-Item -ItemType Directory $RunDirectory | Out-Null
$run=(Resolve-Path -LiteralPath $RunDirectory).Path
New-Item -ItemType Directory "$run\work","$run\outputs","$run\work\ref-build" | Out-Null
Get-ChildItem "$bundle\work" -File | Copy-Item -Destination "$run\work"
Copy-Item "$bundle\work\probe" "$run\work\probe" -Recurse
Expand-Archive "$run\work\source.zip" "$run\work\source"
Expand-Archive "$run\work\iso532-official.zip" "$run\work\official"
Copy-Item "$Repo\data" "$run\work\source\data" -Recurse
$expected=Get-Content "$bundle\outputs\f02-summary.json" -Raw | ConvertFrom-Json
foreach($v in $expected.source.fixture_hashes.PSObject.Properties){
 if((Get-FileHash -LiteralPath (Join-Path "$run\work\source" $v.Name)).Hash.ToLowerInvariant() -ne $v.Value){throw "Fixture mismatch: $($v.Name)"}
}
if((Get-FileHash "$run\work\source.zip").Hash.ToLowerInvariant() -ne $expected.source.archive_sha256){throw 'Source archive mismatch'}
if((Get-FileHash "$run\work\iso532-official.zip").Hash.ToLowerInvariant() -ne $expected.official.zip_sha256){throw 'Official archive mismatch'}
Copy-Item "$bundle\outputs\head.txt" "$run\outputs"
Set-Location -LiteralPath $run
$env:ISO532_F02_PRIOR="$bundle\prior-baseline"
$env:ISO532_LIVE_REPO=$Repo
$env:PYTHONDONTWRITEBYTECODE='1'; $env:REQUIRE_AVX2='1'
function Check([string]$name){$LASTEXITCODE | Set-Content "outputs\$name.exit";if($LASTEXITCODE -ne 0){throw "$name failed. Inspect its log."}}
foreach($script in @('build-reference','build-deep-audit','build-nl')){& "work\$script.cmd" *> "outputs\$script.log"; Check $script}
$env:CARGO_TARGET_DIR="$run\work\target"
cargo test --manifest-path work\source\Cargo.toml --workspace --all-features --locked --offline -- --nocapture *> outputs\cargo-test.log; Check 'cargo-test'
cargo fmt --manifest-path work\source\Cargo.toml --all --check *> outputs\fmt.log; Check 'fmt'
cargo clippy --manifest-path work\source\Cargo.toml --workspace --all-targets --all-features --locked --offline -- -D warnings *> outputs\clippy.log; Check 'clippy'
cargo test --manifest-path work\source\Cargo.toml -p iso532 --test golden_zwtv --locked --offline dump_zwtv_output_hashes -- --ignored --nocapture *> outputs\golden-hashes.log; Check 'golden-hashes'
$env:CARGO_TARGET_DIR="$run\work\probe-target"
cargo build --release --offline --locked --manifest-path work\probe\Cargo.toml *> outputs\probe-build.log; Check 'probe-build'
$env:CARGO_TARGET_DIR="$run\work\binding-target"; $env:PYO3_PYTHON=$BindingPython
cargo build --release --offline --locked --manifest-path work\source\Cargo.toml -p iso532-py -p iso532-ffi *> outputs\binding-build.log; Check 'binding-build'
New-Item -ItemType Directory work\python-bindings | Out-Null
Copy-Item work\binding-target\release\iso532.dll work\python-bindings\iso532.pyd
$env:PYTHONPATH="$run\work\python-bindings"; $env:ISO532_REQUIRE_PARITY='1'
& $BindingPython -m pytest -p no:cacheprovider work\source\iso532-py\tests -q *> outputs\python-tests.log; Check 'python-tests'
foreach($script in @('verify','deep_annex_audit','supplemental','f02_independent')){& $Python "work\$script.py" *> "outputs\$script.log"; Check $script}
& $BindingPython work\f02_bindings.py *> outputs\f02-bindings.log; Check 'f02-bindings'
& $Python work\f02_summary.py *> outputs\f02-summary.log; Check 'f02-summary'
Write-Output 'Read f02-summary.json and all judgments. Exit zero alone does not imply full ISO acceptance.'
