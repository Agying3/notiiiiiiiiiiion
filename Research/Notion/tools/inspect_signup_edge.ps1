$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$processes = Get-CimInstance Win32_Process -Filter "name='msedge.exe'" | Where-Object { $_.CommandLine -like '*run8-edge-direct-20261018-011825*' -and $_.CommandLine -notlike '*--type=*' }
foreach ($process in $processes) {
    $condition = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ProcessIdProperty, [int]$process.ProcessId)
    $windows = [System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children, $condition)
    foreach ($window in $windows) {
        Write-Output ('WINDOW=' + $window.Current.Name)
        $types = @([System.Windows.Automation.ControlType]::Edit, [System.Windows.Automation.ControlType]::Button)
        foreach ($type in $types) {
            $filter = New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::ControlTypeProperty, $type)
            $elements = $window.FindAll([System.Windows.Automation.TreeScope]::Descendants, $filter)
            foreach ($element in $elements) {
                $detail = ''
                if ($type -eq [System.Windows.Automation.ControlType]::Edit) {
                    try {
                        $value = $element.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).Current.Value
                        if ($value -match '^[^\s@]+@[^\s@]+$') { $detail = ' | email=' + $value }
                    } catch {}
                }
                Write-Output ($element.Current.ControlType.ProgrammaticName + ' | ' + $element.Current.Name + ' | enabled=' + $element.Current.IsEnabled + ' | id=' + $element.Current.AutomationId + $detail)
            }
        }
    }
}
