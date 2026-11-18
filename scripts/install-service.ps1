param(
    [Parameter(Mandatory = $true)]
    [string]$PythonPath,
    [Parameter(Mandatory = $true)]
    [string]$ChildAccount
)

$ErrorActionPreference = "Stop"
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this script from an elevated PowerShell window."
}
if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
    throw "PythonPath must point to an existing all-users Python 3.11-3.14 python.exe."
}
$PythonPath = (Resolve-Path -LiteralPath $PythonPath).Path
$programFiles = [IO.Path]::GetFullPath($env:ProgramFiles).TrimEnd('\') + '\'
if (-not $PythonPath.StartsWith($programFiles, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Use an all-users Python installed under Program Files, not a user-writable interpreter."
}
$target = Join-Path $env:ProgramFiles "Kidsroom"
if (Test-Path -LiteralPath $target) {
    throw "$target already exists. Follow README update/uninstall instructions instead of overwriting."
}
New-Item -ItemType Directory -Path $target | Out-Null
$venv = Join-Path $target "runtime"
& $PythonPath -m venv $venv
if ($LASTEXITCODE -ne 0) { throw "Cannot create the service environment in $venv." }
$python = Join-Path $venv "Scripts\python.exe"
$source = Split-Path -Parent $PSScriptRoot
& $python -m pip install $source
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed. Service was not installed." }
& $python -I -m kidsroom.service --startup auto install
if ($LASTEXITCODE -ne 0) { throw "Windows service installation failed." }
& $python -I -m kidsroom.service configure $ChildAccount
if ($LASTEXITCODE -ne 0) { throw "Child account configuration failed. Do not start the service." }
Write-Host ""
Write-Host "Service installed but NOT started."
Write-Host "First sign into the child account and run:"
Write-Host ('  & "' + $venv + '\Scripts\pythonw.exe" -I -m kidsroom')
Write-Host "Set the parent password, add exercises and configure typing."
Write-Host "Then use elevated PowerShell: Start-Service Kidsroom"
