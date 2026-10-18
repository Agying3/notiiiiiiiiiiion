param([Parameter(Mandatory=$true)][string]$Label)
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$procs=Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq 'chrome.exe' -or $_.Name -eq 'msedge.exe') -and $_.CommandLine -like ('*'+$Label+'*') -and $_.CommandLine -notlike '*--type=*' }
foreach($pr in $procs){
  $cond=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ProcessIdProperty,[int]$pr.ProcessId)
  $wins=[System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children,$cond)
  foreach($w in $wins){
    $tc=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Button)
    foreach($b in $w.FindAll([System.Windows.Automation.TreeScope]::Descendants,$tc)){ if($b.Current.Name){ Write-Output ('BTN|'+$b.Current.Name) } }
    $lc=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::ListItem)
    foreach($b in $w.FindAll([System.Windows.Automation.TreeScope]::Descendants,$lc)){ if($b.Current.Name){ Write-Output ('LI|'+$b.Current.Name) } }
    $ec=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Edit)
    foreach($e in $w.FindAll([System.Windows.Automation.TreeScope]::Descendants,$ec)){ $v=''; try{$v=$e.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).Current.Value}catch{}; Write-Output ('ED|'+$e.Current.Name+'|'+$v) }
    return
  }
}