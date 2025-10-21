# Build script for UNESWA WiFi AutoConnect (Windows PowerShell)
# Usage: Open PowerShell as Administrator and run: .\build.ps1

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $projectRoot

# Ensure Python is available
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not available on PATH. Please install Python 3.8+ and add to PATH."
    exit 1
}

# Create and activate virtualenv
$venvPath = Join-Path $projectRoot ".venv_build"
if (-not (Test-Path $venvPath)) {
    python -m venv $venvPath
}
$activate = Join-Path $venvPath "Scripts\Activate.ps1"
. $activate

# Install build deps
pip install --upgrade pip
pip install pyinstaller
pip install -r requirements.txt

## Build with PyInstaller one-file mode (do NOT pass a .spec with --onefile)

# Prepare add-data and hidden-imports
$addData = @(
    "src;src",
    "assets;assets",
    "requirements.txt;."
)
$hiddenImports = @(
    'customtkinter',
    'requests',
    'bs4',
    'psutil',
    'colorlog',
    'configparser'
)

# Icon argument if available
$iconArg = @()
if (Test-Path (Join-Path $projectRoot 'assets\icon.ico')) {
    $iconArg = @('--icon','assets/icon.ico')
}

# Build argument list
$pyArgs = @('--onefile','main.py','--name','UNESWAWiFiAutoConnect','--noconfirm','--clean')

foreach ($d in $addData) { $pyArgs += '--add-data'; $pyArgs += $d }
foreach ($h in $hiddenImports) { $pyArgs += '--hidden-import'; $pyArgs += $h }
if ($iconArg.Count -gt 0) { $pyArgs += $iconArg }

Write-Host "Running: pyinstaller $($pyArgs -join ' ')"
& pyinstaller @pyArgs

# Locate produced exe
$exeName = 'UNESWAWiFiAutoConnect.exe'
$distPath = Join-Path $projectRoot 'dist'
$builtExe = Get-ChildItem -Path $distPath -Recurse -Filter $exeName -ErrorAction SilentlyContinue | Select-Object -First 1

if (-not $builtExe) {
    Write-Error "Build failed or exe not found in dist/*. Check PyInstaller output for errors."
    exit 1
}

# Prepare output folder and copy exe
$packageDir = Join-Path $projectRoot "build_output"
if (Test-Path $packageDir) { Remove-Item $packageDir -Recurse -Force }
New-Item -Path $packageDir -ItemType Directory | Out-Null
Copy-Item -Path $builtExe.FullName -Destination (Join-Path $packageDir $exeName)

Write-Host "Build complete. Single-file exe is in: $packageDir\$exeName"
Write-Host "Tip: Run the exe from the 'build_output' folder to test."