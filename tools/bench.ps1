# Runs the loudness Criterion benchmark and records environment metadata
# alongside the results. Usage:
#   powershell -ExecutionPolicy Bypass -File tools/bench.ps1            # default thread pool (MT)
#   powershell -ExecutionPolicy Bypass -File tools/bench.ps1 -Threads 1 # single-thread baseline
param([int]$Threads = 0)
$ErrorActionPreference = 'Stop'

Set-Location (Join-Path $PSScriptRoot '..\iso532')

if ($Threads -gt 0) { $env:RAYON_NUM_THREADS = "$Threads" }
try {
    cargo bench --bench loudness
    if ($LASTEXITCODE -ne 0) { throw "cargo bench failed with exit code $LASTEXITCODE" }
}
finally {
    Remove-Item Env:RAYON_NUM_THREADS -ErrorAction SilentlyContinue
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$metaDir = 'target\criterion'
New-Item -ItemType Directory -Force -Path $metaDir | Out-Null
@(
    "date: $(Get-Date -Format o)"
    "commit: $(git rev-parse HEAD)"
    "dirty: $([bool](git status --porcelain))"
    "rustc: $(rustc -V)"
    "cpu: $((Get-CimInstance Win32_Processor).Name)"
    "logical_processors: $((Get-CimInstance Win32_ComputerSystem).NumberOfLogicalProcessors)"
    "rayon_threads_arg: $(if ($Threads -gt 0) { $Threads } else { 'default' })"
) | Out-File (Join-Path $metaDir "bench-meta-$stamp.txt") -Encoding utf8

Write-Host "metadata written to $metaDir\bench-meta-$stamp.txt"