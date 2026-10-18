param([Parameter(Mandatory=$true)][string]$Label,[Parameter(Mandatory=$true)][string]$Code)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$procs=Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'chrome.exe' -or $_.Name -eq 'msedge.exe') -and $_.CommandLine -like ('*'+$Label+'*') -and $_.CommandLine -notlike '*--type=*' }
$w=$null
foreach($pr in $procs){
  $cond=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ProcessIdProperty,[int]$pr.ProcessId)
  $wins=[System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children,$cond)
  foreach($x in $wins){ $w=$x; break }
  if($w){ break }
}
if(-not $w){ throw 'window not found' }
$ec=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Edit)
$edits=$w.FindAll([System.Windows.Automation.TreeScope]::Descendants,$ec)
$field=$null
foreach($e in $edits){ if($e.Current.Name -eq '验证码'){ $field=$e; break } }
if(-not $field){ throw 'code field not found' }
$field.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).SetValue($Code)
Start-Sleep -Milliseconds 700
$bc=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty,'继续')
$b=$w.FindFirst([System.Windows.Automation.TreeScope]::Descendants,$bc)
if($b -and $b.Current.IsEnabled){ $b.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke(); Write-Output 'CODE_SUBMITTED' } else { throw 'continue disabled' }