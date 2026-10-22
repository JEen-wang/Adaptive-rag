param(
  [int]$ApiPort = 8002,
  [int]$FrontendPort = 5173
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path ".venv\Scripts\python.exe")) {
  throw "未找到 .venv，请先创建虚拟环境并安装项目依赖。"
}

$env:LOCAL_EMBEDDING_ENABLED = "false"
$env:CROSS_ENCODER_ENABLED = "false"
$env:UNSTRUCTURED_ENABLED = "false"
$env:VITE_API_BASE = "http://127.0.0.1:$ApiPort"

Start-Process -FilePath ".venv\Scripts\python.exe" `
  -ArgumentList "-m", "uvicorn", "app.asgi:app", "--host", "127.0.0.1", "--port", "$ApiPort" `
  -WorkingDirectory $root

Start-Process -FilePath "frontend\.\node_modules\.bin\vite.cmd" `
  -ArgumentList "--host", "127.0.0.1", "--port", "$FrontendPort" `
  -WorkingDirectory (Join-Path $root "frontend")

Write-Host "API:      http://127.0.0.1:$ApiPort"
Write-Host "Frontend: http://127.0.0.1:$FrontendPort"
