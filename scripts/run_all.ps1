<#
.SYNOPSIS
    Runs the whole Nigeria Equity Atlas pipeline in order.

.DESCRIPTION
    Each stage is independently runnable; this is just the canonical order. The script
    stops at the first failing stage, because every stage asserts on its own output and
    a failing assertion means the data is wrong -- continuing would only propagate it.

    Stages 0-3 may hit rate limits on first run and resume automatically from the cache
    in data/raw. Re-running afterwards is offline except for the provenance checks.

.PARAMETER SkipPreviews
    Skip stage 5. Useful when iterating on the workbook, since the PNGs are slow to
    render and are not an input to stage 6.

.EXAMPLE
    .\scripts\run_all.ps1
    .\scripts\run_all.ps1 -SkipPreviews
#>
[CmdletBinding()]
param(
    [switch]$SkipPreviews
)

$ErrorActionPreference = 'Stop'

# Bare `python` on this machine is C:\Python314, a tooling environment with none of the
# required packages. Always use the data-science interpreter explicitly.
$Python = 'C:\Users\TOSHIBA\ds-general\python.exe'
if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python interpreter not found at $Python"
}

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $RepoRoot

$Stages = @(
    '00_validate_reference',
    '01_acquire_mpi',
    '02_acquire_conflict',
    '03_acquire_climate',
    '04_merge',
    '06_build_twb'
)
if (-not $SkipPreviews) {
    # Keep the preview between the merge and the workbook so the visual QA gate always
    # sees freshly merged data.
    $Stages = @(
        '00_validate_reference',
        '01_acquire_mpi',
        '02_acquire_conflict',
        '03_acquire_climate',
        '04_merge',
        '05_preview',
        '06_build_twb'
    )
}

$started = Get-Date
Write-Host ""
Write-Host "Nigeria Equity Atlas -- full pipeline" -ForegroundColor Cyan
Write-Host "  repo    : $RepoRoot"
Write-Host "  python  : $Python"
Write-Host "  stages  : $($Stages.Count)"
Write-Host ""

foreach ($stage in $Stages) {
    $script = Join-Path $PSScriptRoot "$stage.py"
    if (-not (Test-Path -LiteralPath $script)) { throw "missing $script" }

    Write-Host "==> $stage" -ForegroundColor Yellow
    & $Python $script
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "FAILED at $stage (exit $LASTEXITCODE). Fix the cause -- do not relax the" -ForegroundColor Red
        Write-Host "stage's assertions to get past it." -ForegroundColor Red
        exit $LASTEXITCODE
    }
    Write-Host ""
}

$elapsed = (Get-Date) - $started
Write-Host "All $($Stages.Count) stages passed in $([int]$elapsed.TotalSeconds)s" -ForegroundColor Green
Write-Host ""
Write-Host "Workbook : tableau\Nigeria-MPI-Equity-Atlas.twbx"
Write-Host "Next     : docs\PUBLISH.md  (publishing to Tableau Public is a manual step)"
Write-Host ""