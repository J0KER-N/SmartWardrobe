# 从项目根启动后端与前端（在新 PowerShell 窗口中运行）
$root = $PSScriptRoot
$venvActivate = Join-Path $root '..\.venv\Scripts\Activate.ps1'
$pythonExe = Join-Path $root '..\.venv\Scripts\python.exe'

# 先停止已有服务（幂等）
& "$root\stop_services.ps1"

# 启动后端（新窗口，保留窗口便于查看日志）
$backendCmd = "& `"$venvActivate`"; & `"$pythonExe`" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir backend"
Start-Process powershell -ArgumentList "-NoExit","-Command",$backendCmd

# 启动前端（新窗口）
$frontendCmd = "& `"$venvActivate`"; python -m http.server 8080 -d front"
Start-Process powershell -ArgumentList "-NoExit","-Command",$frontendCmd

Write-Output "Started backend (8000) and frontend (8080) in new PowerShell windows."