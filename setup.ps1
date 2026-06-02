# 克隆后首次准备：生成 .env、data 目录、内置 Python（与 setup.bat 逻辑一致）
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
Set-Location $Root

$envFile = Join-Path $Root ".env"
$envExample = Join-Path $Root ".env.example"
if (-not (Test-Path $envFile)) {
    Copy-Item $envExample $envFile
    Write-Host "[setup] 已生成 .env，请填写 DEEPSEEK_API_KEY"
}

$dataDir = Join-Path $Root "data"
if (-not (Test-Path $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir | Out-Null
}

$py = Join-Path $Root "runtime\python\python.exe"
if (Test-Path $py) {
    exit 0
}

Write-Host ""
Write-Host "[setup] 首次使用：正在准备内置 Python（需联网，约 1～3 分钟）..."
Write-Host ""
& (Join-Path $Root "build_portable.ps1")
if ($LASTEXITCODE -ne 0) { exit 1 }
Write-Host ""
Write-Host "[setup] 环境已就绪。"
