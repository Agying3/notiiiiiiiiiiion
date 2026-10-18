param([Parameter(Mandatory=$true)][string]$Label,[Parameter(Mandatory=$true)][string]$Name)
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
$bc=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty,$Name)
$b=$w.FindFirst([System.Windows.Automation.TreeScope]::Descendants,$bc)
if(-not $b){ throw ('button not found: '+$Name) }
$b.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
Write-Output ('CLICKED='+$Name)