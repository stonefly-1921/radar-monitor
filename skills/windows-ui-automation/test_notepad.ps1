Add-Type -AssemblyName System.Windows.Forms
$wshell = New-Object -ComObject WScript.Shell
Start-Sleep -Milliseconds 500
$wshell.AppActivate('Notepad')
Start-Sleep -Milliseconds 200
[System.Windows.Forms.SendKeys]::SendWait('Testing Windows UI Automation - typing into Notepad!')