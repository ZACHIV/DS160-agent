Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$DryRun = $false
$RemoteDebuggingPort = 9222
$CeacUrl = "https://ceac.state.gov/genniv/"
$ProfileDir = Join-Path $RootDir ".visible-browser-profile"

foreach ($arg in $args) {
    switch ($arg) {
        "--dry-run" { $DryRun = $true }
        default { throw "Unknown argument: $arg" }
    }
}

function Resolve-ChromePath {
    $candidates = @(
        "$Env:ProgramFiles\Google\Chrome\Application\chrome.exe",
        "${Env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
        "$Env:LocalAppData\Google\Chrome\Application\chrome.exe",
        "$Env:ProgramFiles\Chromium\Application\chrome.exe",
        "${Env:ProgramFiles(x86)}\Chromium\Application\chrome.exe"
    )

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }

    $command = Get-Command chrome.exe -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    throw "Google Chrome/Chromium not found. Install Chrome for DS-160 autofill."
}

$ChromePath = "chrome.exe"
if (-not $DryRun) {
    $ChromePath = Resolve-ChromePath
}

New-Item -ItemType Directory -Force -Path $ProfileDir | Out-Null

$ChromeArgs = @(
    "--remote-debugging-port=$RemoteDebuggingPort",
    "--user-data-dir=$ProfileDir",
    "--no-first-run",
    "--disable-extensions",
    $CeacUrl
)

if ($DryRun) {
    Write-Output "DRY RUN: scripts/start-chrome-debug-windows.ps1"
    Write-Output ('"{0}" {1}' -f $ChromePath, ($ChromeArgs -join " "))
    exit 0
}

Start-Process -FilePath $ChromePath -ArgumentList $ChromeArgs | Out-Null
Write-Output "Chrome debug window launched on port $RemoteDebuggingPort."
