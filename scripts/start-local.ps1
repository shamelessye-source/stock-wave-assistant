[CmdletBinding()]
param(
    [int]$ApiPort = 8000,
    [int]$WebPort = 5173,
    [string]$BindHost = "127.0.0.1",
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$StateDir = Join-Path $ProjectRoot ".local"
$StatePath = Join-Path $StateDir "local-launcher.json"
$BackendLog = Join-Path $StateDir "backend.log"
$BackendErrorLog = Join-Path $StateDir "backend.err.log"
$FrontendLog = Join-Path $StateDir "frontend.log"
$FrontendErrorLog = Join-Path $StateDir "frontend.err.log"
$ApiUrl = "http://${BindHost}:${ApiPort}"
$WebUrl = "http://${BindHost}:${WebPort}"
$StatePathExistedAtStart = Test-Path -LiteralPath $StatePath
$StateWriteAttempted = $false
$StateWrittenByThisRun = $false
$backend = $null
$frontend = $null

function Require-Command {
    param(
        [string]$Name,
        [string]$InstallHint
    )

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Missing command '$Name'. $InstallHint"
    }
}

function Test-PortAvailable {
    param(
        [string]$Address,
        [int]$Port
    )

    $listener = $null
    try {
        $ip = [System.Net.IPAddress]::Parse($Address)
        $listener = [System.Net.Sockets.TcpListener]::new($ip, $Port)
        $listener.Start()
        return $true
    } catch {
        return $false
    } finally {
        if ($null -ne $listener) {
            $listener.Stop()
        }
    }
}

function Assert-PortAvailable {
    param(
        [string]$Name,
        [int]$Port
    )

    if (-not (Test-PortAvailable -Address $BindHost -Port $Port)) {
        throw "$Name port $Port is already in use. Run scripts\stop-local.ps1 if this project is already running, or retry with -${Name}Port <free-port>."
    }
}

function Wait-HttpReady {
    param(
        [string]$Name,
        [string]$Url
    )

    for ($attempt = 0; $attempt -lt 40; $attempt += 1) {
        try {
            Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2 | Out-Null
            return
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }

    throw "$Name did not become ready at $Url. Check logs under .local and run scripts\stop-local.ps1 before retrying."
}

function Stop-StartedProcess {
    param(
        [string]$Label,
        [object]$Process
    )

    if ($null -eq $Process) {
        return $null
    }

    try {
        $Process.Refresh()
        if (-not $Process.HasExited) {
            Stop-Process -Id $Process.Id -Force -ErrorAction Stop
        }
        return $null
    } catch {
        return "$Label PID $($Process.Id): $($_.Exception.Message)"
    }
}

function Test-InjectedFailure {
    param([string]$Point)

    return (
        -not [string]::IsNullOrWhiteSpace($env:PYTEST_CURRENT_TEST) -and
        $env:STOCK_WAVE_LAUNCHER_TEST_FAILURE -eq $Point
    )
}

function Invoke-TestFailure {
    param([string]$Point)

    if (Test-InjectedFailure -Point $Point) {
        throw "Injected launcher failure at $Point."
    }
}

try {
    if ($StatePathExistedAtStart) {
        throw "Launcher state already exists at .local\local-launcher.json. Run scripts\stop-local.ps1 before starting again."
    }

    Set-Location $ProjectRoot
    New-Item -ItemType Directory -Path $StateDir -Force | Out-Null

    Require-Command "py" "Install Python 3.11+ and make sure the py launcher is available."
    Require-Command "node" "Install Node.js."
    Require-Command "npm.cmd" "Install npm with Node.js."

    & py -c "import fastapi, uvicorn, yaml" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'Python dependencies are missing. Run: py -m pip install -e ".[test]"'
    }

    $ViteScript = Join-Path $ProjectRoot "node_modules\vite\bin\vite.js"
    if (-not (Test-Path -LiteralPath $ViteScript)) {
        throw "Node dependencies are missing. Run: npm.cmd install"
    }

    Assert-PortAvailable -Name "Api" -Port $ApiPort
    Assert-PortAvailable -Name "Web" -Port $WebPort

    Write-Host "Starting backend at $ApiUrl ..."
    $backend = Start-Process `
        -FilePath "py" `
        -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", $BindHost, "--port", $ApiPort.ToString()) `
        -WorkingDirectory $ProjectRoot `
        -PassThru `
        -WindowStyle Hidden `
        -RedirectStandardOutput $BackendLog `
        -RedirectStandardError $BackendErrorLog

    $previousApiBase = $env:VITE_API_BASE_URL
    $env:VITE_API_BASE_URL = $ApiUrl
    try {
        Write-Host "Starting web app at $WebUrl ..."
        Invoke-TestFailure -Point "frontend_start"
        $ViteScriptArgument = "`"$ViteScript`""
        $frontend = Start-Process `
            -FilePath "node" `
            -ArgumentList @($ViteScriptArgument, "--host", $BindHost, "--port", $WebPort.ToString()) `
            -WorkingDirectory $ProjectRoot `
            -PassThru `
            -WindowStyle Hidden `
            -RedirectStandardOutput $FrontendLog `
            -RedirectStandardError $FrontendErrorLog
    } finally {
        $env:VITE_API_BASE_URL = $previousApiBase
    }

    $state = [pscustomobject]@{
        projectRoot = $ProjectRoot
        startedAt = (Get-Date).ToString("o")
        backend = [pscustomobject]@{
            pid = $backend.Id
            port = $ApiPort
            url = $ApiUrl
            log = ".local/backend.log"
            errorLog = ".local/backend.err.log"
        }
        frontend = [pscustomobject]@{
            pid = $frontend.Id
            port = $WebPort
            url = $WebUrl
            log = ".local/frontend.log"
            errorLog = ".local/frontend.err.log"
        }
    }
    $StateWriteAttempted = $true
    if (Test-InjectedFailure -Point "state_write") {
        Set-Content -LiteralPath $StatePath -Value '{"incomplete":' -Encoding UTF8
        throw "Injected launcher failure at state_write after creating incomplete state file."
    }
    $state | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $StatePath -Encoding UTF8
    $StateWrittenByThisRun = $true

    Wait-HttpReady -Name "Backend" -Url "$ApiUrl/api/health"
    Wait-HttpReady -Name "Web app" -Url $WebUrl

    Write-Host ""
    Write-Host "Stock Wave Assistant is running:"
    Write-Host "  Web: $WebUrl"
    Write-Host "  API: $ApiUrl"
    Write-Host ""
    Write-Host "To stop it, run:"
    Write-Host "  scripts\stop-local.ps1"
    Write-Host ""

    if (-not $NoBrowser) {
        try {
            Invoke-TestFailure -Point "browser_open"
            Start-Process $WebUrl
        } catch {
            Write-Warning "Browser could not be opened. Open $WebUrl manually. $($_.Exception.Message)" -WarningAction Continue
        }
    }
} catch {
    $startupError = $_.Exception.Message
    $cleanupErrors = @()

    foreach ($entry in @(
        @{ label = "frontend"; process = $frontend },
        @{ label = "backend"; process = $backend }
    )) {
        $cleanupError = Stop-StartedProcess `
            -Label $entry.label `
            -Process $entry.process
        if ($null -ne $cleanupError) {
            $cleanupErrors += $cleanupError
        }
    }

    $keepStateForRetry = $StateWrittenByThisRun -and $cleanupErrors.Count -gt 0
    if (
        -not $StatePathExistedAtStart -and
        $StateWriteAttempted -and
        -not $keepStateForRetry -and
        (Test-Path -LiteralPath $StatePath)
    ) {
        try {
            Remove-Item -LiteralPath $StatePath -Force -ErrorAction Stop
        } catch {
            $cleanupErrors += "state file: $($_.Exception.Message)"
        }
    }

    Write-Error $startupError -ErrorAction Continue
    if ($cleanupErrors.Count -gt 0) {
        Write-Warning "Startup rollback was incomplete: $($cleanupErrors -join '; '). Check .local logs and run scripts\stop-local.ps1 if a launcher state file remains."
    }
    exit 1
}
