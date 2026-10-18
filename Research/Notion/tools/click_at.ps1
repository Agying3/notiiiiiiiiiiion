param([Parameter(Mandatory=$true)][string]$Label,[Parameter(Mandatory=$true)][int]$X,[Parameter(Mandatory=$true)][int]$Y,[int]$RefW=1280,[int]$RefH=720)
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class W {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, IntPtr e);
  [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr h, ref POINT p);
  public struct RECT { public int Left, Top, Right, Bottom; }
  public struct POINT { public int X, Y; }
}
"@
$procs=Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'chrome.exe' -or $_.Name -eq 'msedge.exe') -and $_.CommandLine -like ('*'+$Label+'*') -and $_.CommandLine -notlike '*--type=*' }
$hwndVal=0
foreach($pr in $procs){
  $cond=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ProcessIdProperty,[int]$pr.ProcessId)
  $wins=[System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children,$cond)
  foreach($el in $wins){
    $hnd=[int]$el.Current.NativeWindowHandle
    if($hnd -gt 0){ $hwndVal=$hnd; break }
  }
  if($hwndVal -gt 0){ break }
}
if($hwndVal -le 0){ throw 'window handle not found' }
$hwnd=[IntPtr]::new([int64]$hwndVal)
[void][W]::SetForegroundWindow($hwnd)
Start-Sleep -Milliseconds 700
$r=New-Object W+RECT
[void][W]::GetClientRect($hwnd,[ref]$r)
$cw=$r.Right-$r.Left; $ch=$r.Bottom-$r.Top
$pt=New-Object W+POINT
$pt.X=0; $pt.Y=0
[void][W]::ClientToScreen($hwnd,[ref]$pt)
$sx=[int]($pt.X + $X*$cw/$RefW)
$sy=[int]($pt.Y + $Y*$ch/$RefH)
[void][W]::SetCursorPos($sx,$sy)
Start-Sleep -Milliseconds 300
[W]::mouse_event(0x0002,0,0,0,[IntPtr]::Zero)
[W]::mouse_event(0x0004,0,0,0,[IntPtr]::Zero)
Write-Output ("CLICKED x=$sx y=$sy client=${cw}x${ch}")