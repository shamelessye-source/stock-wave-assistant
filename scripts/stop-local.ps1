[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$StateDir = Join-Path $ProjectRoot ".local"
$StatePath = Join-Path $StateDir "local-launcher.json"
$script:HadSkippedProcess = $false

function Get-RecordedProcess {
    param([int]$ProcessIdValue)

    try {
        return Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessIdValue"
    } catch {
        return $null
    }
}

function Test-CommandLineContains {
    param(
        [string]$CommandLine,
        [string[]]$Patterns
    )

    foreach ($pattern in $Patterns) {
        if ($CommandLine -notlike "*$pattern*") {
            return $false
        }
    }
    return $true
}

function Stop-RecordedProcess {
    param(
        [string]$Label,
        [object]$Entry,
        [string[]]$CommandLinePatterns
    )

    if ($null -eq $Entry -or $null -eq $Entry.pid) {
        Write-Host "$Label process was not recorded."
        return
    }

    $processId = [int]$Entry.pid
    $recordedProcess = Get-RecordedProcess -ProcessIdValue $processId
    if ($null -eq $recordedProcess) {
        Write-Host "$Label process $processId is already stopped."
        return
    }

    $commandLine = [string]$recordedProcess.CommandLine
    if (-not (Test-CommandLineContains -CommandLine $commandLine -Patterns $CommandLinePatterns)) {
        Write-Warning "$Label process $processId does not match this project's launcher command. It was not stopped."
        $script:HadSkippedProcess = $true
        return
    }

    Stop-Process -Id $processId -Force
    Write-Host "Stopped $Label process $processId."
}

if (-not (Test-Path -LiteralPath $StatePath)) {
    Write-Host "No local launcher state file found. Nothing to stop."
    exit 0
}

try {
    $state = Get-Content -LiteralPath $StatePath -Raw -Encoding UTF8 | ConvertFrom-Json
} catch {
    Write-Error "Could not read .local\local-launcher.json. Remove it manually if it is stale."
    exit 1
}

if ([string]$state.projectRoot -ne $ProjectRoot) {
    Write-Error "The launcher state file belongs to another project path. It was not used."
    exit 1
}

Stop-RecordedProcess `
    -Label "frontend" `
    -Entry $state.frontend `
    -CommandLinePatterns @("vite", "--port", ([string]$state.frontend.port))

Stop-RecordedProcess `
    -Label "backend" `
    -Entry $state.backend `
    -CommandLinePatterns @("uvicorn", "app.main:app", "--port", ([string]$state.backend.port))

if ($script:HadSkippedProcess) {
    Write-Warning "Some recorded processes were skipped. The state file was kept for inspection: .local\local-launcher.json"
    exit 1
}

Remove-Item -LiteralPath $StatePath -Force
Write-Host "Local launcher state cleared."
