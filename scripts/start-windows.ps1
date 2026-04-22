Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$DryRun = $false
$ChromeScript = Join-Path $RootDir "scripts\start-chrome-debug-windows.ps1"
$LogDir = Join-Path $RootDir ".logs"
$ServerLog = Join-Path $LogDir "server.log"
$PowerShellHost = (Get-Process -Id $PID).Path

foreach ($arg in $args) {
    switch ($arg) {
        "--dry-run" { $DryRun = $true }
        default { throw "Unknown argument: $arg" }
    }
}

function Get-FileUrl {
    param([string]$Path)
    return ([System.Uri] (Resolve-Path $Path)).AbsoluteUri
}

function Test-ServerUp {
    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:8765/status" -UseBasicParsing | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Resolve-PythonBin {
    $venvPython = Join-Path $RootDir ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        return $venvPython
    }

    $pyCommand = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($pyCommand) {
        return $pyCommand.Source
    }

    $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        return $pythonCommand.Source
    }

    throw "Python not found. Install Python 3 or create .venv first."
}

$IntakeUrl = Get-FileUrl (Join-Path $RootDir "app\intake.html")
$AssistantUrl = Get-FileUrl (Join-Path $RootDir "app\ds160-assistant.html")
$PythonBin = "python.exe"
$PythonArgs = @("-m", "visa_agent.server")

if (-not $DryRun) {
    $PythonBin = Resolve-PythonBin
    if ($PythonBin -like "*py.exe") {
        $PythonArgs = @("-3", "-m", "visa_agent.server")
    }
}

if ($DryRun) {
    & $PowerShellHost -NoProfile -File $ChromeScript --dry-run
    Write-Output "DRY RUN: scripts/start-windows.ps1"
    Write-Output ('set PYTHONPATH={0}\src && "{1}" {2}' -f $RootDir, $PythonBin, ($PythonArgs -join " "))
    Write-Output ('start "" "{0}"' -f $IntakeUrl)
    Write-Output ('start "" "{0}"' -f $AssistantUrl)
    exit 0
}

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

& $PowerShellHost -NoProfile -File $ChromeScript

if (Test-ServerUp) {
    Write-Output "FastAPI server is already running on http://127.0.0.1:8765"
} else {
    $escapedRootDir = $RootDir.Replace("'", "''")
    $escapedPythonPath = (Join-Path $RootDir "src").Replace("'", "''")
    $escapedPythonBin = $PythonBin.Replace("'", "''")
    $escapedServerLog = $ServerLog.Replace("'", "''")
    $pythonArgsLiteral = ($PythonArgs | ForEach-Object { "'{0}'" -f ($_.Replace("'", "''")) }) -join ", "
    $serverCommand = "& { Set-Location '$escapedRootDir'; `$env:PYTHONPATH = '$escapedPythonPath'; & '$escapedPythonBin' @($pythonArgsLiteral) *> '$escapedServerLog' }"

    $serverProcess = Start-Process `
        -FilePath $PowerShellHost `
        -ArgumentList @("-NoProfile", "-Command", $serverCommand) `
        -WorkingDirectory $RootDir `
        -PassThru

    Write-Output "Starting FastAPI server (pid $($serverProcess.Id)), log: $ServerLog"

    for ($i = 0; $i -lt 15; $i++) {
        if (Test-ServerUp) {
            break
        }
        Start-Sleep -Seconds 1
    }

    if (-not (Test-ServerUp)) {
        Write-Error "FastAPI server did not become ready. Recent log output:`n$((Get-Content -Path $ServerLog -Tail 20 -ErrorAction SilentlyContinue) -join [Environment]::NewLine)"
    }
}

Start-Process $IntakeUrl | Out-Null
Start-Process $AssistantUrl | Out-Null

@"
Windows startup complete.

- Intake page: $IntakeUrl
- Assistant page: $AssistantUrl
- FastAPI service: http://127.0.0.1:8765
- Chrome remote debugging: http://127.0.0.1:9222/json/version

Note: The local intake/assistant pages are opened with your default Windows browser.
DS-160 autofill still depends on Google Chrome/Chromium because the backend uses Chrome DevTools Protocol.
"@ | Write-Output
