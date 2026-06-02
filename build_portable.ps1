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
$py = Join-Path $PyDir "python.exe"
$req = Join-Path $Root "requirements-portable.txt"

function Invoke-Download {
    param([string]$Uri, [string]$OutFile)
    Invoke-WebRequest -Uri $Uri -OutFile $OutFile -UseBasicParsing -TimeoutSec 300
}

function Test-RuntimeReady {
    if (-not (Test-Path $py)) { return $false }
    & $py -c "import fastapi, uvicorn, sqlalchemy" 2>$null
    return $LASTEXITCODE -eq 0
}

function Install-PipRequirements {
    param([string]$PythonExe, [string]$RequirementsFile)
    # Explicit mirrors + long timeout; avoids a slow global pip.ini mirror blocking install
    $env:PIP_DISABLE_PIP_VERSION_CHECK = "1"
    $mirrors = @(
        @{ Url = "https://pypi.org/simple"; Host = "pypi.org" },
        @{ Url = "https://mirrors.aliyun.com/pypi/simple"; Host = "mirrors.aliyun.com" },
        @{ Url = "https://pypi.mirrors.ustc.edu.cn/simple"; Host = "pypi.mirrors.ustc.edu.cn" },
        @{ Url = "https://mirrors.cloud.tencent.com/pypi/simple"; Host = "mirrors.cloud.tencent.com" },
        @{ Url = "https://pypi.tuna.tsinghua.edu.cn/simple"; Host = "pypi.tuna.tsinghua.edu.cn" }
    )
    $pipArgs = @(
        "-m", "pip", "install", "-r", $RequirementsFile,
        "--no-warn-script-location",
        "--default-timeout=120",
        "--retries", "8"
    )
    foreach ($m in $mirrors) {
        Write-Host "Installing dependencies (mirror: $($m.Host))..."
        & $PythonExe @pipArgs "-i", $m.Url, "--trusted-host", $m.Host
        if ($LASTEXITCODE -eq 0) { return }
        Write-Host "Mirror failed, trying next..."
    }
    throw "pip install failed on all mirrors. Check network or proxy, then run build_portable.bat again."
}

if (Test-RuntimeReady) {
    Write-Host "Runtime already ready."
    exit 0
}

if (Test-Path $py) {
    Write-Host "Python found; finishing dependency install..."
    Install-PipRequirements -PythonExe $py -RequirementsFile $req
    Write-Host "Verify..."
    & $py -c "import fastapi, uvicorn, sqlalchemy; print('OK')"
    Write-Host "Done. Run run.bat to start."
    exit 0
}

Write-Host "Downloading Python embed..."
Invoke-Download -Uri $Url -OutFile $Zip
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
Invoke-Download -Uri $GetPipUrl -OutFile $GetPip
& $py $GetPip --no-warn-script-location
if ($LASTEXITCODE -ne 0) { throw "get-pip failed" }
Remove-Item $GetPip -Force

Install-PipRequirements -PythonExe $py -RequirementsFile $req

Write-Host "Verify..."
& $py -c "import fastapi, uvicorn, sqlalchemy; print('OK')"
Write-Host "Done. Run run.bat to start."
