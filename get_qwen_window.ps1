Add-Type -AssemblyName System.Windows.Forms
$proc = Get-Process -Id 21024
$hwnd = $proc.MainWindowHandle
$rect = New-Object System.Windows.Forms.Rectangle
$bounds = $proc.MainWindowBounds
Write-Output "HWND=$hwnd Left=$($bounds.Left) Top=$($bounds.Top) Right=$($bounds.Right) Bottom=$($bounds.Bottom)"
Write-Output "Width=$($bounds.Width) Height=$($bounds.Height)"