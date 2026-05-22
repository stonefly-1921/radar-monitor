using System;
using System.Runtime.InteropServices;
using System.Drawing;

class QwenWin {
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left, Top, Right, Bottom; }
    static void Main() {
        IntPtr hWnd = (IntPtr)133298;
        RECT r;
        GetWindowRect(hWnd, out r);
        int w = r.Right - r.Left;
        int h = r.Bottom - r.Top;
        Console.WriteLine("Left=" + r.Left + " Top=" + r.Top + " Width=" + w + " Height=" + h);
    }
}