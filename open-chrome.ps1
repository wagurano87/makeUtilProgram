$ErrorActionPreference = 'Stop'
try {
    $null = Invoke-RestMethod 'http://127.0.0.1:9222/json/version' -TimeoutSec 2
    Write-Host 'Chrome is already available. Log in there, then run WEBSCRAP.'
    return
} catch { }
$candidates = @(
    (Join-Path $env:ProgramFiles 'Google\Chrome\Application\chrome.exe'),
    (Join-Path ${env:ProgramFiles(x86)} 'Google\Chrome\Application\chrome.exe'),
    (Join-Path $env:LOCALAPPDATA 'Google\Chrome\Application\chrome.exe')
)
$chrome = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $chrome) { throw 'Google Chrome is required. Install Chrome first.' }
$profile = Join-Path $env:LOCALAPPDATA 'WEBSCRAP\ChromeProfile'
# Chrome 136+ requires a non-default profile for remote debugging.
# Reuse the earlier WEBSCRAP profile; never copy the regular Chrome profile.
Start-Process -FilePath $chrome -ArgumentList @(
    '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=9222',
    "--user-data-dir=`"$profile`"", 'https://nid.naver.com/nidlogin.login'
)
Write-Host 'Log in in the opened Chrome and leave it open. Then run WEBSCRAP.'
Write-Host 'If that profile was already open without debugging, close only that Chrome window and run this script again.'
