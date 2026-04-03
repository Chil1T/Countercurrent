[CmdletBinding()]
param(
    [string]$WorkspaceRoot = "",
    [string]$BindHost = "127.0.0.1",
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3000,
    [int]$HealthTimeoutSeconds = 60,
    [string]$PythonCommand = "python",
    [string]$NpmCommand = "npm",
    [string]$NpxCommand = "npx",
    [switch]$NoCleanPorts,
    [switch]$SkipBackendInstall,
    [switch]$SkipFrontendInstall,
    [switch]$ExitWhenReady,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$script:TrackedProcesses = @()
$script:ChildProcessJobHandle = [IntPtr]::Zero
$script:CleanupPerformed = $false

function Ensure-JobObjectType {
    if ("JobObjectNative" -as [type]) {
        return
    }

    Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

public static class JobObjectNative
{
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
    public static extern IntPtr CreateJobObject(IntPtr lpJobAttributes, string lpName);

    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool AssignProcessToJobObject(IntPtr hJob, IntPtr hProcess);

    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool SetInformationJobObject(
        IntPtr hJob,
        JOBOBJECTINFOCLASS JobObjectInfoClass,
        IntPtr lpJobObjectInfo,
        UInt32 cbJobObjectInfoLength);

    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool CloseHandle(IntPtr hObject);

    public const UInt32 JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000;

    public enum JOBOBJECTINFOCLASS
    {
        JobObjectExtendedLimitInformation = 9
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct JOBOBJECT_BASIC_LIMIT_INFORMATION
    {
        public Int64 PerProcessUserTimeLimit;
        public Int64 PerJobUserTimeLimit;
        public UInt32 LimitFlags;
        public UIntPtr MinimumWorkingSetSize;
        public UIntPtr MaximumWorkingSetSize;
        public UInt32 ActiveProcessLimit;
        public IntPtr Affinity;
        public UInt32 PriorityClass;
        public UInt32 SchedulingClass;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct IO_COUNTERS
    {
        public UInt64 ReadOperationCount;
        public UInt64 WriteOperationCount;
        public UInt64 OtherOperationCount;
        public UInt64 ReadTransferCount;
        public UInt64 WriteTransferCount;
        public UInt64 OtherTransferCount;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct JOBOBJECT_EXTENDED_LIMIT_INFORMATION
    {
        public JOBOBJECT_BASIC_LIMIT_INFORMATION BasicLimitInformation;
        public IO_COUNTERS IoInfo;
        public UIntPtr ProcessMemoryLimit;
        public UIntPtr JobMemoryLimit;
        public UIntPtr PeakProcessMemoryUsed;
        public UIntPtr PeakJobMemoryUsed;
    }
}
"@
}

function Initialize-ChildProcessJob {
    Ensure-JobObjectType

    if ($script:ChildProcessJobHandle -ne [IntPtr]::Zero) {
        return
    }

    $jobHandle = [JobObjectNative]::CreateJobObject([IntPtr]::Zero, "ReCurr-GUI-$PID")
    if ($jobHandle -eq [IntPtr]::Zero) {
        throw "Failed to create process job object."
    }

    $info = New-Object "JobObjectNative+JOBOBJECT_EXTENDED_LIMIT_INFORMATION"
    $info.BasicLimitInformation.LimitFlags = [JobObjectNative]::JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE

    $infoSize = [System.Runtime.InteropServices.Marshal]::SizeOf($info)
    $infoPtr = [System.Runtime.InteropServices.Marshal]::AllocHGlobal($infoSize)
    try {
        [System.Runtime.InteropServices.Marshal]::StructureToPtr($info, $infoPtr, $false)
        $success = [JobObjectNative]::SetInformationJobObject(
            $jobHandle,
            [JobObjectNative+JOBOBJECTINFOCLASS]::JobObjectExtendedLimitInformation,
            $infoPtr,
            [uint32]$infoSize
        )
        if (-not $success) {
            throw "Failed to configure process job object."
        }
    }
    finally {
        [System.Runtime.InteropServices.Marshal]::FreeHGlobal($infoPtr)
    }

    $script:ChildProcessJobHandle = $jobHandle
}

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

function Quote-CmdArgument {
    param(
        [string]$Value
    )

    return '"' + $Value.Replace('"', '""') + '"'
}

function Resolve-PythonCommandInfo {
    param(
        [string]$Command
    )

    if ([string]::IsNullOrWhiteSpace($Command)) {
        throw "PythonCommand cannot be empty."
    }

    $commandInfo = Get-Command $Command -ErrorAction Stop | Select-Object -First 1
    $resolvedPath = $commandInfo.Source
    if ([string]::IsNullOrWhiteSpace($resolvedPath)) {
        $resolvedPath = $commandInfo.Path
    }
    if ([string]::IsNullOrWhiteSpace($resolvedPath)) {
        throw "Failed to resolve Python command: $Command"
    }

    $versionOutput = (& $resolvedPath --version 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to inspect Python version from: $resolvedPath"
    }

    $match = [regex]::Match($versionOutput, 'Python\s+(?<major>\d+)\.(?<minor>\d+)(?:\.(?<patch>\d+))?')
    if (-not $match.Success) {
        throw "Failed to parse Python version from: $versionOutput"
    }

    $major = [int]$match.Groups["major"].Value
    $minor = [int]$match.Groups["minor"].Value
    $patch = if ($match.Groups["patch"].Success) { [int]$match.Groups["patch"].Value } else { 0 }

    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 10)) {
        throw "GUI local start requires Python 3.10+; resolved $resolvedPath -> $versionOutput"
    }

    return [PSCustomObject]@{
        Path    = $resolvedPath
        Version = "$major.$minor.$patch"
        Raw     = $versionOutput
    }
}

function Start-HiddenTrackedProcess {
    param(
        [string]$WorkingDirectory,
        [string]$FilePath,
        [string]$Arguments,
        [string]$Name
    )

    Initialize-ChildProcessJob

    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $FilePath
    $startInfo.Arguments = $Arguments
    $startInfo.WorkingDirectory = $WorkingDirectory
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden

    $process = [System.Diagnostics.Process]::Start($startInfo)
    if ($null -eq $process) {
        throw "Failed to start $Name process."
    }

    $assigned = [JobObjectNative]::AssignProcessToJobObject($script:ChildProcessJobHandle, $process.Handle)
    if (-not $assigned) {
        try {
            if (-not $process.HasExited) {
                $process.Kill()
            }
        }
        catch {
        }

        throw "Failed to assign $Name process to controller job object."
    }

    $script:TrackedProcesses += [PSCustomObject]@{
        Name    = $Name
        Process = $process
    }

    return $process
}

function Stop-TrackedProcesses {
    if ($script:CleanupPerformed) {
        return
    }

    $script:CleanupPerformed = $true

    foreach ($tracked in $script:TrackedProcesses) {
        $process = $tracked.Process
        if ($null -eq $process) {
            continue
        }

        try {
            if (-not $process.HasExited) {
                Write-Host "Stopping $($tracked.Name) process $($process.Id)"
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            }
        }
        finally {
            $process.Dispose()
        }
    }

    $script:TrackedProcesses = @()

    if ($script:ChildProcessJobHandle -ne [IntPtr]::Zero) {
        [JobObjectNative]::CloseHandle($script:ChildProcessJobHandle) | Out-Null
        $script:ChildProcessJobHandle = [IntPtr]::Zero
    }
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
    Remove-Item -LiteralPath $backendLog -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $frontendLog -Force -ErrorAction SilentlyContinue

    Write-Host "Workspace root: $workspace"
    Write-Host "Backend log: $backendLog"
    Write-Host "Frontend log: $frontendLog"
    Write-Host "Backend health: $backendHealthUrl"
    Write-Host "Frontend health: $frontendHealthUrl"

    $pythonInfo = Resolve-PythonCommandInfo -Command $PythonCommand
    Write-Host "Resolved Python command: $($pythonInfo.Path)"
    Write-Host "Resolved Python version: $($pythonInfo.Raw)"

    if (-not $NoCleanPorts) {
        Write-Host "Cleaning ports: $BackendPort, $FrontendPort"
        if (-not $DryRun) {
            Stop-ListeningProcesses -Ports @($BackendPort, $FrontendPort)
        }
    }

    $resolvedPythonCommand = $pythonInfo.Path
    $backendPythonForCmd = Quote-CmdArgument $resolvedPythonCommand
    $backendInstallCommand = "& $(Quote-CommandSegment $resolvedPythonCommand) -m pip install -r $(Quote-CommandSegment (Join-Path $workspace 'server\\requirements.txt'))"
    $frontendInstallCommand = "& $(Quote-CommandSegment $NpmCommand) install"
    $backendRuntimeCommand = "$backendPythonForCmd -m uvicorn server.app.main:app --host $BindHost --port $BackendPort"
    $frontendRuntimeCommand = "$NpxCommand next dev --hostname $BindHost --port $FrontendPort"
    $backendStartCommand = "$backendRuntimeCommand > $(Quote-CmdArgument $backendLog) 2>&1"
    $frontendStartCommand = "$frontendRuntimeCommand > $(Quote-CmdArgument $frontendLog) 2>&1"
    $backendShellCommand = "& $(Quote-CommandSegment $resolvedPythonCommand) -m uvicorn server.app.main:app --host $BindHost --port $BackendPort *> $(Quote-CommandSegment $backendLog)"
    $frontendShellCommand = "& $(Quote-CommandSegment $NpxCommand) next dev --hostname $BindHost --port $FrontendPort *> $(Quote-CommandSegment $frontendLog)"
    $hiddenShell = "powershell.exe"
    $backendHiddenArguments = "-NoProfile -ExecutionPolicy Bypass -Command $(Quote-CmdArgument $backendShellCommand)"
    $frontendHiddenArguments = "-NoProfile -ExecutionPolicy Bypass -Command $(Quote-CmdArgument $frontendShellCommand)"

    if (-not $SkipBackendInstall) {
        Write-Host "Backend install command: $backendInstallCommand"
        if (-not $DryRun) {
            & $resolvedPythonCommand -m pip install -r (Join-Path $workspace "server\requirements.txt")
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

    $backendProcess = Start-HiddenTrackedProcess `
        -WorkingDirectory $workspace `
        -FilePath $hiddenShell `
        -Arguments $backendHiddenArguments `
        -Name "backend"

    $frontendProcess = Start-HiddenTrackedProcess `
        -WorkingDirectory $webRoot `
        -FilePath $hiddenShell `
        -Arguments $frontendHiddenArguments `
        -Name "frontend"

    Wait-Http200 -Url $backendHealthUrl -TimeoutSeconds $HealthTimeoutSeconds
    Wait-Http200 -Url $frontendHealthUrl -TimeoutSeconds $HealthTimeoutSeconds

    Write-Host "GUI local development stack is ready."
    Write-Host "Controller window is active. Close this window or press Ctrl+C to stop backend and frontend."
    Write-Host "Backend PID: $($backendProcess.Id)"
    Write-Host "Frontend PID: $($frontendProcess.Id)"

    if ($ExitWhenReady) {
        Write-Host "ExitWhenReady enabled. Verified both services and exiting controller."
        exit 0
    }

    while ($true) {
        foreach ($tracked in $script:TrackedProcesses) {
            if ($tracked.Process.HasExited) {
                throw "$($tracked.Name) process exited unexpectedly. Check its log file for details."
            }
        }

        Start-Sleep -Seconds 2
    }
}
catch {
    Write-Error $_
    exit 1
}
finally {
    Stop-TrackedProcesses
}
