$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    & py -3 -m venv (Join-Path $root '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.10+ is required. Install Python with the py launcher.' }
}
& $python -m pip install -r (Join-Path $root 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
$env:PLAYWRIGHT_BROWSERS_PATH = '0'
& $python -m playwright install chromium
if ($LASTEXITCODE -ne 0) { throw 'Chromium installation failed.' }
$escapedPython = $python.Replace("'", "''")
$escapedScript = (Join-Path $root 'webscrap.py').Replace("'", "''")
$function = "function global:WEBSCRAP { & '$escapedPython' '$escapedScript' @args }"
# Append only if this exact installation is not already registered.
$profileDir = Split-Path -Parent $PROFILE
New-Item -ItemType Directory -Force -Path $profileDir | Out-Null
if (-not (Test-Path $PROFILE)) { New-Item -ItemType File -Path $PROFILE | Out-Null }
$existing = Get-Content -Raw $PROFILE
if (-not $existing -or -not $existing.Contains($function)) {
    Add-Content -Path $PROFILE -Value "`r`n$function" -Encoding UTF8
}
Invoke-Expression $function
Write-Host 'Installed. Run: WEBSCRAP "https://example.com"'
