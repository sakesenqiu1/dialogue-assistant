# Run once with internet to create portable runtime (Windows 64-bit)
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Rt = Join-Path $Root "runtime"
$PyDir = Join-Path $Rt "python"
$Lib = Join-Path $Rt "Lib\site-packages"
$Zip = Join-Path $env:TEMP "python-embed.zip"
$Url = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-embed-amd64.zip"
$GetPip = Join-Path $env:TEMP "get-pip.py"
$GetPipUrl = "https://bootstrap.pypa.io/get-pip.py"

Write-Host "Downloading Python embed..."
Invoke-WebRequest -Uri $Url -OutFile $Zip -UseBasicParsing
if (Test-Path $PyDir) { Remove-Item $PyDir -Recurse -Force }
New-Item -ItemType Directory -Force -Path $PyDir | Out-Null
Expand-Archive -Path $Zip -DestinationPath $PyDir -Force
Remove-Item $Zip -Force

New-Item -ItemType Directory -Force -Path $Lib | Out-Null

$pth = Get-ChildItem $PyDir -Filter "python*._pth" | Select-Object -First 1
if (-not $pth) { throw "._pth not found" }
@(
    "python312.zip",
    ".",
    "..\Lib\site-packages",
    "",
    "import site"
) | Set-Content $pth.FullName -Encoding ASCII

Write-Host "Installing pip..."
Invoke-WebRequest -Uri $GetPipUrl -OutFile $GetPip -UseBasicParsing
$py = Join-Path $PyDir "python.exe"
& $py $GetPip --no-warn-script-location
Remove-Item $GetPip -Force

Write-Host "Installing dependencies..."
$req = Join-Path $Root "requirements-portable.txt"
& $py -m pip install -r $req --no-warn-script-location -q

Write-Host "Verify..."
& $py -c "import fastapi, uvicorn, sqlalchemy; print('OK')"
Write-Host "Done. Copy folder 222 to any PC and run run.bat"
