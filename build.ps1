# CoteabMacro Build Script
# Usage: .\build.ps1
# Optional: .\build.ps1 -SkipFrontend  (skip npm build step)
param(
    [switch]$SkipFrontend
)

$ErrorActionPreference = "Stop"
$ROOT = $PSScriptRoot

# ---- Locate Python (prefer venv, then system) ----
$PYTHON = $null
foreach ($candidate in @(
    "$ROOT\venv\Scripts\python.exe",
    "$ROOT\.venv\Scripts\python.exe"
)) {
    if (Test-Path $candidate) {
        $PYTHON = $candidate
        break
    }
}
if (-not $PYTHON) {
    # Fall back to system python - prefer 3.12 then anything
    foreach ($cmd in @("py -3.12", "py", "python")) {
        try {
            $PYTHON = (& cmd /c "$cmd -c `"import sys; print(sys.executable)`" 2>nul").Trim()
            if ($PYTHON -and (Test-Path $PYTHON)) { break }
        } catch { }
    }
}
if (-not $PYTHON -or -not (Test-Path $PYTHON)) {
    Write-Error "Could not find a Python executable. Make sure venv exists or Python is installed."
    exit 1
}
Write-Host "Using Python: $PYTHON" -ForegroundColor Cyan

# ---- Build Frontend ----
if (-not $SkipFrontend) {
    Write-Host "`nBuilding frontend..." -ForegroundColor Yellow
    Push-Location "$ROOT\frontend"
    & npm run build
    if ($LASTEXITCODE -ne 0) { Pop-Location; Write-Error "Frontend build failed!"; exit 1 }
    Pop-Location

    Write-Host "Copying dist to lib/dist..." -ForegroundColor Yellow
    if (Test-Path "$ROOT\lib\dist") { Remove-Item "$ROOT\lib\dist" -Recurse -Force }
    Copy-Item "$ROOT\frontend\dist" "$ROOT\lib\dist" -Recurse
}

# ---- Run PyInstaller via venv Python ----
Write-Host "`nRunning PyInstaller..." -ForegroundColor Yellow
& $PYTHON -m PyInstaller --clean --noconfirm "CoteabMacro-onefile.spec"
if ($LASTEXITCODE -ne 0) { Write-Error "PyInstaller build failed!"; exit 1 }

Write-Host "`nBuild complete! Output: dist\CoteabMacro.exe" -ForegroundColor Green
