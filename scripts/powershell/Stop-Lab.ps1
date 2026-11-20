#requires -Version 5.1
# Graceful AWS stop only. Never terminate, force shutdown or delete mirroring implicitly.
[CmdletBinding()]
param([string]$ConfigPath,[switch]$Apply)
. (Join-Path $PSScriptRoot 'Common.ps1')
$c = Read-LabConfig -ConfigPath $ConfigPath
Assert-LabAccount -Config $c
$instances = @(Get-LabInstances -Config $c)
Show-LabInventory -Config $c
$sessions = @(Get-LabMirrors -Config $c)
if ($sessions.Count -gt 0) {
    $sessions | Select-Object TrafficMirrorSessionId,TrafficMirrorTargetId,TrafficMirrorFilterId | Format-Table -AutoSize
    throw 'Mirroring session(s) still present on this source. Review and delete only the authorized test session first; EC2 stop alone will not stop those charges.'
}
if (-not $Apply) { Write-Host 'PREVIEW ONLY. Add -Apply to stop Worker, Zeek and Control Plane. EBS charges continue.'; return }
foreach ($role in @('worker','zeek','control-plane')) {
    $node = Get-LabNode -Config $c -Role $role
    $current = @(Get-LabInstances -Config $c | Where-Object { $_.InstanceId -eq $node.instanceId })[0]
    if ($current.State.Name -eq 'pending') {
        Invoke-LabAws -Config $c -AwsArguments @('ec2','wait','instance-running','--instance-ids',$node.instanceId) | Out-Null
        $current = @(Get-LabInstances -Config $c | Where-Object { $_.InstanceId -eq $node.instanceId })[0]
    }
    if ($current.State.Name -eq 'running') {
        Write-Host "Stopping $role ($($node.instanceId))"
        Invoke-LabAws -Config $c -AwsArguments @('ec2','stop-instances','--instance-ids',$node.instanceId) | Out-Null
    } elseif ($current.State.Name -notin @('stopping','stopped')) {
        throw "Refusing unexpected state for ${role}: $($current.State.Name)"
    }
    Invoke-LabAws -Config $c -AwsArguments @('ec2','wait','instance-stopped','--instance-ids',$node.instanceId) | Out-Null
}
Show-LabInventory -Config $c
Write-Host 'All three configured instances are stopped. EBS storage and any other independent resources remain billable.'
