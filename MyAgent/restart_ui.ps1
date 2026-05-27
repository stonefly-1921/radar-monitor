# Restart MyAgent UI

$existing = Get-Process -Name python | Where-Object { $_.MainWindowTitle -eq "MyAgent v2.1" }
if ($existing) {
    Write-Host "[CLOSE] PID=$($existing.Id)"
    Stop-Process -Id $existing.Id -Force
    Start-Sleep 2
}

Write-Host "[START] MyAgent UI..."
$proc = Start-Process "D:\anaconda3\python.exe" `
    -ArgumentList "C:\Users\15041\.openclaw\workspace\MyAgent\agent\ui.py" `
    -WorkingDirectory "C:\Users\15041\.openclaw\workspace\MyAgent" `
    -PassThru

Write-Host "Starting PID=$($proc.Id)..."
Start-Sleep 4

$running = Get-Process -Name python | Where-Object { $_.MainWindowTitle -eq "MyAgent v2.1" }
if ($running) {
    Write-Host "[OK] MyAgent UI running PID=$($running.Id)"
    $repl = Get-WmiObject Win32_Process | Where-Object { $_.ParentProcessId -eq $running.Id }
    $repl | ForEach-Object { Write-Host "  Child: PID=$($_.ProcessId) $($_.Name)" }
} else {
    Write-Host "[FAIL] MyAgent UI not started"
}