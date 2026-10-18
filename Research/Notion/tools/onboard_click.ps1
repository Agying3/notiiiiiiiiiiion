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
if(-not $w){ throw 'window not found' }
function Click-Named([string]$n){
  foreach($t in @([System.Windows.Automation.ControlType]::Button,[System.Windows.Automation.ControlType]::Text,[System.Windows.Automation.ControlType]::Hyperlink)){
    $c=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty,$n)
    $el=$w.FindFirst([System.Windows.Automation.TreeScope]::Descendants,$c)
    if($el){ try{ $el.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke(); return $true }catch{} }
  }
  return $false
}
Write-Output ('COOKIE=' + (Click-Named '全部拒绝'))
Start-Sleep -Seconds 2
Write-Output ('CONTINUE=' + (Click-Named '继续'))