param(
    [string]$PythonPath = (Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe")
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = (Resolve-Path -LiteralPath $PythonPath).Path
& $python -c "import struct, sys; sys.exit(0 if sys.platform == 'win32' and struct.calcsize('P') == 8 else 1)"
if ($LASTEXITCODE -ne 0) { throw "Use 64-bit Python on Windows to build this distribution." }
& $python -m PyInstaller --noconfirm --clean `
    --distpath (Join-Path $root "dist") `
    --workpath (Join-Path $root "build\pyinstaller") `
    (Join-Path $root "packaging\Kidsroom.spec")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }
$bundle = Join-Path $root "dist\Kidsroom"
& $python (Join-Path $root "scripts\bundle-notices.py") $bundle
if ($LASTEXITCODE -ne 0) { throw "Cannot collect dependency license notices." }
Copy-Item -LiteralPath (Join-Path $root "README.md") -Destination $bundle
Copy-Item -LiteralPath (Join-Path $root "packaging\PORTABLE.txt") `
    -Destination (Join-Path $bundle "BAT-DAU.txt")
Copy-Item -LiteralPath (Join-Path $root "scripts\install-bundled-service.ps1") `
    -Destination (Join-Path $bundle "Install-Service.ps1")
$version = & $python -c "import pathlib,tomllib; print(tomllib.loads(pathlib.Path(r'$root\pyproject.toml').read_text(encoding='utf-8'))['project']['version'])"
if ($LASTEXITCODE -ne 0) { throw "Cannot read package version." }
$archive = Join-Path $root ("dist\Kidsroom-" + $version + "-Windows-x64.zip")
Compress-Archive -LiteralPath $bundle -DestinationPath $archive -Force
Write-Host "Executable: $(Join-Path $bundle 'Kidsroom.exe')"
Write-Host "Portable ZIP: $archive"
