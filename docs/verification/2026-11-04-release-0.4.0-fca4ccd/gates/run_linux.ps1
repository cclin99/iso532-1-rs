# Run from the repository root after run_gates.py has staged inputs.
$ErrorActionPreference = 'Stop'
$base = Join-Path (Get-Location) 'tmp/acceptance-040-astra/linux'
$out = Join-Path (Get-Location) 'docs/verification/2026-11-04-release-0.4.0-fca4ccd/gates'
New-Item -ItemType Directory -Force $base | Out-Null
python -c "import subprocess,pathlib;pathlib.Path('tmp/acceptance-040-astra/linux/source.tar').write_bytes(subprocess.check_output(['git','archive','fca4ccda18a8fbada77031425e5e683f1acd5a8d']))"
Copy-Item (Join-Path $out 'run_linux.sh') (Join-Path $base 'run.sh')
docker image inspect ubuntu:24.04 --format '{{.Id}}' | Set-Content -Encoding utf8 (Join-Path $out 'linux-image.txt')
docker run --rm --name iso532-astra-040-linux -v "${base}:/input:ro" ubuntu:24.04 bash /input/run.sh *> (Join-Path $out 'linux.log')
$LASTEXITCODE | Set-Content (Join-Path $out 'linux-exit.txt')
