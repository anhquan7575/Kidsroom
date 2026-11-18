param(
    [string]$ChildAccount
)

$ErrorActionPreference = "Stop"
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run PowerShell as Administrator before installing the service."
}
if ([string]::IsNullOrWhiteSpace($ChildAccount)) {
    $ChildAccount = Read-Host "Windows child account (example: COMPUTER\child)"
}
$account = New-Object Security.Principal.NTAccount($ChildAccount)
$account.Translate([Security.Principal.SecurityIdentifier]) | Out-Null
foreach ($name in @("Kidsroom.exe", "KidsroomService.exe", "_internal")) {
    if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot $name))) {
        throw "Extract the complete ZIP first; missing $name."
    }
}
if (Get-Service -Name Kidsroom -ErrorAction SilentlyContinue) {
    throw "Kidsroom service already exists. Stop/remove the previous service before installing."
}
$target = Join-Path $env:ProgramFiles "Kidsroom"
if (Test-Path -LiteralPath $target) {
    throw "$target already exists. Do not overwrite a running or source-mode installation."
}
New-Item -ItemType Directory -Path $target | Out-Null
foreach ($entry in Get-ChildItem -LiteralPath $PSScriptRoot -Force) {
    Copy-Item -LiteralPath $entry.FullName -Destination $target -Recurse
}
$service = Join-Path $target "KidsroomService.exe"
& $service --startup auto install
if ($LASTEXITCODE -ne 0) { throw "Service installation failed." }
& $service configure $ChildAccount
if ($LASTEXITCODE -ne 0) { throw "Child account configuration failed. Do not start the service." }
Write-Host "Service installed but NOT started."
Write-Host "Before rebooting, sign into the child account and open:"
Write-Host (Join-Path $target "Kidsroom.exe")
Write-Host "Set the parent password and configure lessons."
Write-Host "Then use Administrator PowerShell: Start-Service Kidsroom"
