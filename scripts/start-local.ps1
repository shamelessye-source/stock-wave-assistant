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

try {
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

    if (Test-Path -LiteralPath $StatePath) {
        Write-Warning "Existing launcher state file found at .local\local-launcher.json. If this is stale, run scripts\stop-local.ps1."
    }

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
        $frontend = Start-Process `
            -FilePath "node" `
            -ArgumentList @($ViteScript, "--host", $BindHost, "--port", $WebPort.ToString()) `
            -WorkingDirectory $ProjectRoot `
            -PassThru `
            -WindowStyle Hidden `
            -RedirectStandardOutput $FrontendLog `
            -RedirectStandardError $FrontendErrorLog
    } finally {
        $env:VITE_API_BASE_URL = $previousApiBase
    }

    [pscustomobject]@{
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
    } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $StatePath -Encoding UTF8

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
        Start-Process $WebUrl
    }
} catch {
    Write-Error $_.Exception.Message
    exit 1
}
