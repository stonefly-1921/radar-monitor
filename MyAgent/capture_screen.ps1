Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$bmp = New-Object System.Drawing.Bitmap([System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width, [System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Height)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen(0, 0, 0, 0, (New-Object System.Drawing.Size($bmp.Width, $bmp.Height)))
$bmp.Save("C:\Users\15041\.openclaw\workspace\MyAgent\ui_screenshot.png")
$g.Dispose()
$bmp.Dispose()
Write-Host "Screenshot saved"