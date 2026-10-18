param(
  [string]$AccountFile = 'accounts.txt',
  [string]$EmailPrefix = ''
)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$t=[System.IO.File]::ReadAllText($AccountFile,[System.Text.Encoding]::UTF8)
$line=($t -split "`r?`n" | Where-Object { $_ -like ($EmailPrefix + '*') } | Select-Object -First 1)
$cred=(($line -split '----')[1]).Trim()
$procs=Get-CimInstance Win32_Process -Filter "name='msedge.exe'" | Where-Object { $_.CommandLine -like '*playwright*' -or $_.CommandLine -like '*mcp*' }
$done=$false
foreach($pr in $procs){
  $cond=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ProcessIdProperty,[int]$pr.ProcessId)
  $wins=[System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children,$cond)
  foreach($w in $wins){
    $ec=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Edit)
    $edits=$w.FindAll([System.Windows.Automation.TreeScope]::Descendants,$ec)
    foreach($e in $edits){
      if($e.Current.IsPassword -and $e.Current.IsEnabled){
        $e.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).SetValue($cred)
        Start-Sleep -Milliseconds 400
        $bc=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty,[System.Windows.Automation.ControlType]::Button)
        $btns=$w.FindAll([System.Windows.Automation.TreeScope]::Descendants,$bc)
        foreach($b in $btns){
          if($b.Current.Name -eq '登录' -or $b.Current.Name -eq '下一步'){
            $b.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
            Write-Output ('SUBMITTED_BY=' + $b.Current.Name)
            $done=$true; break
          }
        }
      }
      if($done){ break }
    }
    if($done){ break }
  }
  if($done){ break }
}
if(-not $done){ throw 'password field not found' }