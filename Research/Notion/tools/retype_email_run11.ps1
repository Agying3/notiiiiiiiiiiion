$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$email='[REDACTED_EMAIL]'
function Get-Window {
  $procs=Get-CimInstance Win32_Process -Filter "name='chrome.exe'" | Where-Object { $_.CommandLine -like '*run11-auto-signup*' -and $_.CommandLine -notlike '*--type=*' }
  foreach($pr in $procs){
    $cond=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ProcessIdProperty,[int]$pr.ProcessId)
    $wins=[System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children,$cond)
    foreach($w in $wins){ return $w }
  }
  return $null
}
$w=Get-Window
if(-not $w){ throw 'window not found' }
$ec=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Edit)
$edits=$w.FindAll([System.Windows.Automation.TreeScope]::Descendants,$ec)
$mailField=$null
foreach($e in $edits){ if($e.Current.Name -eq '工作邮件'){ $mailField=$e; break } }
if(-not $mailField){ throw 'mail field not found' }
$mailField.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).SetValue($email)
Start-Sleep -Milliseconds 800
function Click-Continue {
  $bc=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty,'继续')
  $b=$w.FindFirst([System.Windows.Automation.TreeScope]::Descendants,$bc)
  if($b -and $b.Current.IsEnabled){ $b.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke(); return $true }
  return $false
}
Click-Continue | Out-Null
Write-Output 'FIRST_CLICK'
Start-Sleep -Seconds 14
Click-Continue | Out-Null
Write-Output 'SECOND_CLICK'