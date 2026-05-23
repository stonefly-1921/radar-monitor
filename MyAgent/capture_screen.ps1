Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$folder = Join-Path $env:USERPROFILE ".openclaw\media"
if (-not (Test-Path $folder)) { New-Item -ItemType Directory -Path $folder | Out-Null }
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$filename = "screenshot_$timestamp.png"
$path = Join-Path $folder $filename
$screen = [System.Windows.Forms.Screen]::PrimaryScreen
$bitmap = New-Object System.Drawing.Bitmap($screen.WorkingArea.Width, $screen.WorkingArea.Height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($screen.WorkingArea.Location, [System.Drawing.Point]::Empty, $screen.WorkingArea.Size)
$bitmap.Save($path)
$graphics.Dispose()
$bitmap.Dispose()
Write-Output "SAVED:$path"