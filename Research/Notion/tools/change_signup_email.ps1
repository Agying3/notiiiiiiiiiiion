param(
    [Parameter(Mandatory=$true)][string]$NewEmail,
    [string]$OldEmail = '[REDACTED_EMAIL]'
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$processes = Get-CimInstance Win32_Process -Filter "name='msedge.exe'" | Where-Object { $_.CommandLine -like '*run8-edge-direct-20261018-011825*' -and $_.CommandLine -notlike '*--type=*' }
$target = $null
$mailField = $null
foreach ($process in $processes) {
    $condition = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ProcessIdProperty, [int]$process.ProcessId)
    $windows = [System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children, $condition)
    foreach ($window in $windows) {
        $editCondition = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Edit)
        $fields = $window.FindAll([System.Windows.Automation.TreeScope]::Descendants, $editCondition)
        foreach ($field in $fields) {
            try {
                $value = $field.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).Current.Value
                if ($value -eq $OldEmail -or $field.Current.Name -eq '工作邮件') { $target = $window; $mailField = $field; break }
            } catch {}
        }
        if ($target) { break }
    }
    if ($target) { break }
}
if (-not $target) { throw 'Signup email field not found in the run8 Edge window; nothing changed' }
$setValue = $mailField.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern)
$setValue.SetValue($NewEmail)
$buttonCondition = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty, '继续')
$button = $target.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $buttonCondition)
if (-not $button -or -not $button.Current.IsEnabled) { throw 'Continue button unavailable after email change' }
$button.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
Write-Output ('EMAIL_CHANGED_AND_SUBMITTED=' + $NewEmail + '; same window kept open')
