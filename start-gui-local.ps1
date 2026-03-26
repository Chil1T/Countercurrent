[CmdletBinding()]
param(
    [string]$WorkspaceRoot = "",
    [string]$BindHost = "127.0.0.1",
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3000,
    [int]$HealthTimeoutSeconds = 60,
    [string]$PythonCommand = "python",
    [string]$NpmCommand = "npm",
    [switch]$NoCleanPorts,
    [switch]$SkipBackendInstall,
    [switch]$SkipFrontendInstall,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-WorkspaceLayout {
    param(
        [string]$Root
    )

    if (-not (Test-Path -LiteralPath $Root -PathType Container)) {
        throw "Workspace root does not exist: $Root"
    }

    $requiredDirs = @(
        (Join-Path $Root "server"),
        (Join-Path $Root "web")
    )

    foreach ($dir in $requiredDirs) {
        if (-not (Test-Path -LiteralPath $dir -PathType Container)) {
            throw "Workspace root is missing required directory: $dir"
        }
    }

    $serverRequirements = Join-Path $Root "server\requirements.txt"
    $webPackage = Join-Path $Root "web\package.json"

    if (-not (Test-Path -LiteralPath $serverRequirements -PathType Leaf)) {
        throw "Workspace root is missing required file: $serverRequirements"
    }

    if (-not (Test-Path -LiteralPath $webPackage -PathType Leaf)) {
        throw "Workspace root is missing required file: $webPackage"
    }
}

function Stop-ListeningProcesses {
    param(
        [int[]]$Ports
    )

    foreach ($port in $Ports) {
        $connections = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        $processIds = $connections | Select-Object -ExpandProperty OwningProcess -Unique
        foreach ($processId in $processIds) {
            if ($null -ne $processId) {
                Write-Host "Stopping process $processId on port $port"
                Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

function Wait-Http200 {
    param(
        [string]$Url,
        [int]$TimeoutSeconds
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 5
            if ($response.StatusCode -eq 200) {
                Write-Host "Health check passed: $Url"
                return
            }
        }
        catch {
            Start-Sleep -Seconds 1
            continue
        }

        Start-Sleep -Seconds 1
    }

    throw "Health check timed out: $Url"
}

function Quote-CommandSegment {
    param(
        [string]$Value
    )

    return "'" + $Value.Replace("'", "''") + "'"
}

try {
    if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
        $scriptPath = $MyInvocation.MyCommand.Path
        if ([string]::IsNullOrWhiteSpace($scriptPath)) {
            throw "Workspace root was not provided and script path could not be resolved."
        }

        $WorkspaceRoot = Split-Path -Parent $scriptPath
    }

    Assert-WorkspaceLayout -Root $WorkspaceRoot

    $workspace = (Resolve-Path -LiteralPath $WorkspaceRoot).ProviderPath
    $webRoot = Join-Path $workspace "web"
    $guiOutDir = Join-Path $workspace "out\_gui"
    $backendLog = Join-Path $guiOutDir "backend-dev.log"
    $frontendLog = Join-Path $guiOutDir "frontend-dev.log"
    $backendHealthUrl = "http://$BindHost`:$BackendPort/healthz"
    $frontendHealthUrl = "http://$BindHost`:$FrontendPort/courses/new/input"

    New-Item -ItemType Directory -Path $guiOutDir -Force | Out-Null

    Write-Host "Workspace root: $workspace"
    Write-Host "Backend log: $backendLog"
    Write-Host "Frontend log: $frontendLog"
    Write-Host "Backend health: $backendHealthUrl"
    Write-Host "Frontend health: $frontendHealthUrl"

    if (-not $NoCleanPorts) {
        Write-Host "Cleaning ports: $BackendPort, $FrontendPort"
        if (-not $DryRun) {
            Stop-ListeningProcesses -Ports @($BackendPort, $FrontendPort)
        }
    }

    $backendInstallCommand = "& $(Quote-CommandSegment $PythonCommand) -m pip install -r $(Quote-CommandSegment (Join-Path $workspace 'server\\requirements.txt'))"
    $frontendInstallCommand = "& $(Quote-CommandSegment $NpmCommand) install"
    $backendStartCommand = "& $(Quote-CommandSegment $PythonCommand) -m uvicorn server.app.main:app --host $BindHost --port $BackendPort *> $(Quote-CommandSegment $backendLog)"
    $frontendStartCommand = "& $(Quote-CommandSegment $NpmCommand) run dev -- --hostname $BindHost --port $FrontendPort *> $(Quote-CommandSegment $frontendLog)"

    if (-not $SkipBackendInstall) {
        Write-Host "Backend install command: $backendInstallCommand"
        if (-not $DryRun) {
            & $PythonCommand -m pip install -r (Join-Path $workspace "server\requirements.txt")
        }
    }

    if (-not $SkipFrontendInstall) {
        Write-Host "Frontend install command: $frontendInstallCommand"
        if (-not $DryRun) {
            Push-Location $webRoot
            try {
                & $NpmCommand install
            }
            finally {
                Pop-Location
            }
        }
    }

    Write-Host "Backend start command: $backendStartCommand"
    Write-Host "Frontend start command: $frontendStartCommand"

    if ($DryRun) {
        Write-Host "Dry run mode enabled. No processes were started."
        exit 0
    }

    Start-Process -FilePath "powershell.exe" `
        -ArgumentList @("-NoLogo", "-NoProfile", "-Command", $backendStartCommand) `
        -WorkingDirectory $workspace | Out-Null

    Start-Process -FilePath "powershell.exe" `
        -ArgumentList @("-NoLogo", "-NoProfile", "-Command", $frontendStartCommand) `
        -WorkingDirectory $webRoot | Out-Null

    Wait-Http200 -Url $backendHealthUrl -TimeoutSeconds $HealthTimeoutSeconds
    Wait-Http200 -Url $frontendHealthUrl -TimeoutSeconds $HealthTimeoutSeconds

    Write-Host "GUI local development stack is ready."
}
catch {
    Write-Error $_
    exit 1
}
