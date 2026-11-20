#requires -Version 5.1
[CmdletBinding()]
param([string]$ConfigPath)
. (Join-Path $PSScriptRoot 'Common.ps1')
$c = Read-LabConfig -ConfigPath $ConfigPath
Assert-LabAccount -Config $c
Show-LabInventory -Config $c
$sessions = @(Get-LabMirrors -Config $c)
Write-Host "Traffic Mirror sessions on the configured source ENI: $($sessions.Count)"
if ($sessions.Count -gt 0) {
    $sessions | Select-Object TrafficMirrorSessionId,TrafficMirrorTargetId,TrafficMirrorFilterId | Format-Table -AutoSize
    Write-Warning 'Stopping EC2 does not stop these mirroring charges. Review ownership before deletion.'
}
