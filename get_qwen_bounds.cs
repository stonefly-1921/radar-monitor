Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
using System.Text;
using System.Drawing;
public class WindowHelper {
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
    [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
    public static Rectangle GetBounds(IntPtr hWnd) {
        RECT r; GetWindowRect(hWnd, out r);
        return new Rectangle(r.Left, r.Top, r.Right - r.Left, r.Bottom - r.Top);
    }
}
"@ -ReferencedAssemblies System.Drawing

$proc = Get-Process -Id 21024
$hwnd = $proc.MainWindowHandle
$bounds = [WindowHelper]::GetBounds($hwnd)
Write-Output "Left=$($bounds.Left) Top=$($bounds.Top) Width=$($bounds.Width) Height=$($bounds.Height)"