# 重启服务：先停止，再启动
$root = $PSScriptRoot
& "$root\stop_services.ps1"
Start-Sleep -Seconds 1
& "$root\start_services.ps1"
Write-Output "Restart sequence executed."