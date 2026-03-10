# INGRVM Windows Service Installer (Phase 7 Task #2)
# Configures the INGRVM Neural Node to run automatically on user login.

$NodeDir = Get-Location
$PythonPath = (Get-Command python).Source
$LauncherPath = "$NodeDir\launch_node_background.vbs"
$LogFile = "$NodeDir\logs\service_activity.log"

Write-Host "--- 🛠️ INGRVM Node Service Setup ---" -ForegroundColor Cyan

# 1. Create a VBScript launcher to run Python without a terminal window popping up
$VBSContent = @"
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "$PythonPath $NodeDir\neural_node.py", 0, False
"@
$VBSContent | Out-File -FilePath $LauncherPath -Encoding utf8

# 2. Register the Scheduled Task
$TaskName = "INGRVMNeuralNode"
$Action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument $LauncherPath -WorkingDirectory $NodeDir
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

Write-Host "[1/2] Registering Windows Scheduled Task: $TaskName..."
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "INGRVM Neuromorphic Mesh Node"

Write-Host "[2/2] Setup complete."
Write-Host "✅ The node will now start automatically whenever you log in." -ForegroundColor Green
Write-Host "To start it manually now, run: Start-ScheduledTask -TaskName $TaskName"

