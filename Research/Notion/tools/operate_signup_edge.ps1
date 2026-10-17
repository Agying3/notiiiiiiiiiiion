param(
    [ValidateSet('resend','submit')] [string]$Action,
    [string]$Email = '[REDACTED_EMAIL]',
    [string]$CodeFile
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$processes = Get-CimInstance Win32_Process -Filter "name='msedge.exe'" | Where-Object { $_.CommandLine -like '*run8-edge-direct-20261018-011825*' -and $_.CommandLine -notlike '*--type=*' }
$target = $null
foreach ($process in $processes) {
    $condition = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ProcessIdProperty, [int]$process.ProcessId)
    $windows = [System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children, $condition)
    foreach ($window in $windows) {
        $mailCondition = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Edit)
        $mailFields = $window.FindAll([System.Windows.Automation.TreeScope]::Descendants, $mailCondition)
        foreach ($mailField in $mailFields) {
            try {
                $value = $mailField.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).Current.Value
                if ($value -eq $Email) { $target = $window; break }
            } catch {}
        }
        if ($target) { break }
    }
}
if (-not $target) { throw 'Current signup mailbox was not verified in the Edge accessibility tree; no action taken' }
if ($Action -eq 'submit') {
    $private = Get-Content -LiteralPath $CodeFile -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($private.email -ne $Email -or $private.code -notmatch '^\d{4,8}$') { throw 'Code record does not match current mailbox' }
    $editCondition = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Edit)
    $edits = $target.FindAll([System.Windows.Automation.TreeScope]::Descendants, $editCondition)
    $field = $null
    foreach ($edit in $edits) { if ($edit.Current.Name -eq '验证码' -and $edit.Current.IsEnabled) { $field = $edit } }
    if (-not $field) { throw 'Verification input not found' }
    $pattern = $field.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern)
    $pattern.SetValue([string]$private.code)
    $buttonName = '继续'
} else { $buttonName = '重新发送验证码' }
$buttonCondition = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty, $buttonName)
$button = $target.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $buttonCondition)
if (-not $button -or -not $button.Current.IsEnabled) { throw 'Requested signup button not available' }
$invoke = $button.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
$invoke.Invoke()
Write-Output ('SIGNUP_ACTION_DONE=' + $Action + '; email verified; existing browser kept open')
