param([Parameter(Mandatory=$true)][string]$Label)
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
$all=$w.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition)
foreach($e in $all){
  $n=$e.Current.Name
  if($n -and ($n -like '*工作*' -or $n -like '*私人*' -or $n -like '*学校*' -or $n -like '*继续*')){ Write-Output ($e.Current.ControlType.ProgrammaticName+'|'+$n.Substring(0,[Math]::Min(40,$n.Length))+'|id='+$e.Current.AutomationId) }
}