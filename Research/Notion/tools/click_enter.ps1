param([Parameter(Mandatory=$true)][string]$Label,[Parameter(Mandatory=$true)][int]$ScreenX,[Parameter(Mandatory=$true)][int]$ScreenY)
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class K {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x,int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f,uint dx,uint dy,uint d,IntPtr e);
  [DllImport("user32.dll")] public static extern void keybd_event(byte vk,byte scan,uint f,IntPtr extra);
}
"@
$procs=Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'chrome.exe' -or $_.Name -eq 'msedge.exe') -and $_.CommandLine -like ('*'+$Label+'*') -and $_.CommandLine -notlike '*--type=*' }
$hw=0
foreach($pr in $procs){
  $cond=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ProcessIdProperty,[int]$pr.ProcessId)
  foreach($el in [System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children,$cond)){ $h=[int]$el.Current.NativeWindowHandle; if($h -gt 0){ $hw=$h; break } }
  if($hw -gt 0){ break }
}
if($hw -le 0){ throw 'no window' }
[void][K]::SetForegroundWindow([IntPtr]::new([int64]$hw))
Start-Sleep -Milliseconds 500
[void][K]::SetCursorPos($ScreenX,$ScreenY)
Start-Sleep -Milliseconds 300
[K]::mouse_event(0x0002,0,0,0,[IntPtr]::Zero); [K]::mouse_event(0x0004,0,0,0,[IntPtr]::Zero)
Start-Sleep -Milliseconds 800
[K]::keybd_event(0x0D,0,0,[IntPtr]::Zero); [K]::keybd_event(0x0D,0,2,[IntPtr]::Zero)
Write-Output "CLICK_AND_ENTER done"