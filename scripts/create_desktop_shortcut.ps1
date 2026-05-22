$W = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktop 'SmartWardrobe Start.lnk'
$sc = $W.CreateShortcut($shortcutPath)
$sc.TargetPath = 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
$sc.Arguments = '-ExecutionPolicy Bypass -NoExit -File "C:\Users\23708\Desktop\smart-wardrobe-system\scripts\start_services.ps1"'
$sc.WorkingDirectory = 'C:\Users\23708\Desktop\smart-wardrobe-system'
$sc.IconLocation = 'C:\Windows\System32\shell32.dll,1'
$sc.Save()
Write-Output "Shortcut created at $shortcutPath"