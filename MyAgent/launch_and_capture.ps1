$proc = Start-Process -FilePath 'D:\anaconda3\python.exe' -ArgumentList 'C:\Users\15041\.openclaw\workspace\MyAgent\agent\ui.py' -WorkingDirectory 'C:\Users\15041\.openclaw\workspace\MyAgent' -PassThru
Start-Sleep -Seconds 4
& powershell -File 'C:\Users\15041\.openclaw\workspace\MyAgent\capture_screen.ps1'
Start-Sleep -Seconds 1
Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
Write-Host 'Done'