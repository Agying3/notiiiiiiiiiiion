$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$processes = Get-CimInstance Win32_Process -Filter "name='chrome.exe'" | Where-Object { $_.CommandLine -like '*run11-auto-signup*' -and $_.CommandLine -notlike '*--type=*' }
foreach ($process in $processes) {
    $condition = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ProcessIdProperty, [int]$process.ProcessId)
    $windows = [System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children, $condition)
    foreach ($window in $windows) {
        Write-Output ('WINDOW=' + $window.Current.Name)
        $editCondition = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Edit)
        $edits = $window.FindAll([System.Windows.Automation.TreeScope]::Descendants, $editCondition)
        foreach ($edit in $edits) {
            $value = ''
            try { $value = $edit.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).Current.Value } catch {}
            Write-Output ('EDIT | ' + $edit.Current.Name + ' | value=' + $value)
        }
        $buttonCondition = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Button)
        $buttons = $window.FindAll([System.Windows.Automation.TreeScope]::Descendants, $buttonCondition)
        foreach ($button in $buttons) { Write-Output ('BUTTON | ' + $button.Current.Name) }
    }
}
