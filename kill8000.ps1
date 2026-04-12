$procs = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
foreach ($p in $procs) {
    $proc = Get-Process -Id $p.OwningProcess -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Host "Killing PID $($proc.Id) $($proc.ProcessName) from $($proc.Path)"
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
}
