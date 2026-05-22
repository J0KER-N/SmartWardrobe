# 停止占用端口 8000 和 8080 的进程
$ports = 8000,8080
foreach ($port in $ports) {
    $connections = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($connections) {
        $connections | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {
            try { Stop-Process -Id $_ -Force -ErrorAction Stop } catch { }
        }
    }
}
Write-Output "Stopped processes listening on ports: $($ports -join ', ')"