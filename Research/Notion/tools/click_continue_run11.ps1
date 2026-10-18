$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$processes = Get-CimInstance Win32_Process -Filter "name='chrome.exe'" | Where-Object { $_.CommandLine -like '*run11-auto-signup*' -and $_.CommandLine -notlike '*--type=*' }
foreach ($process in $processes) {
    $condition = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ProcessIdProperty, [int]$process.ProcessId)
    $windows = [System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children, $condition)
    foreach ($window in $windows) {
        $buttonCondition = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty, '继续')
        $button = $window.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $buttonCondition)
        if ($button -and $button.Current.IsEnabled) {
            $button.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
            Write-Output 'CONTINUE_CLICKED'
            return
        }
    }
}
throw 'Continue button not found or disabled in run11 window'
