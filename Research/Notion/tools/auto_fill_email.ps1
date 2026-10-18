param(
    [Parameter(Mandatory=$true)][string]$Email
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$processes = Get-CimInstance Win32_Process -Filter "name='chrome.exe'" | Where-Object { $_.CommandLine -like '*run11-auto-signup*' -and $_.CommandLine -notlike '*--type=*' }
$target = $null; $mailField = $null
foreach ($process in $processes) {
    $condition = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ProcessIdProperty, [int]$process.ProcessId)
    $windows = [System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children, $condition)
    foreach ($window in $windows) {
        $editCondition = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Edit)
        $fields = $window.FindAll([System.Windows.Automation.TreeScope]::Descendants, $editCondition)
        foreach ($field in $fields) {
            if ($field.Current.Name -eq '工作邮件' -and $field.Current.IsEnabled) { $target = $window; $mailField = $field; break }
        }
        if ($target) { break }
    }
    if ($target) { break }
}
if (-not $target) { throw 'Email field not found in run11 window' }
$mailField.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).SetValue($Email)
Start-Sleep -Milliseconds 600
$buttonCondition = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty, '继续')
$button = $target.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $buttonCondition)
if (-not $button -or -not $button.Current.IsEnabled) { throw 'Continue button unavailable' }
$button.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
Write-Output ('EMAIL_SUBMITTED=' + $Email)
