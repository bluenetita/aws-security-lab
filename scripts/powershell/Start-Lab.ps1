#requires -Version 5.1
# Starts existing instances only. No launch, mirroring, security-group or deployment changes.
[CmdletBinding()]
param([string]$ConfigPath,[switch]$IncludeWorker,[switch]$Apply)
. (Join-Path $PSScriptRoot 'Common.ps1')
$c = Read-LabConfig -ConfigPath $ConfigPath
Assert-LabAccount -Config $c
$instances = @(Get-LabInstances -Config $c)
$roles = @('control-plane','zeek')
if ($IncludeWorker) {
    Write-Warning 'Verify actual node placement and local image availability before using historical manifests; see docs/source-availability.md.'
    $roles += 'worker'
}
Write-Host ('Selected roles: ' + ($roles -join ', '))
Show-LabInventory -Config $c
if (-not $Apply) { Write-Host 'PREVIEW ONLY. Add -Apply to start existing instances (AWS charges resume).'; return }
foreach ($role in $roles) {
    $node = Get-LabNode -Config $c -Role $role
    $current = @(Get-LabInstances -Config $c | Where-Object { $_.InstanceId -eq $node.instanceId })[0]
    if ($current.State.Name -eq 'stopping') {
        Invoke-LabAws -Config $c -AwsArguments @('ec2','wait','instance-stopped','--instance-ids',$node.instanceId) | Out-Null
        $current = @(Get-LabInstances -Config $c | Where-Object { $_.InstanceId -eq $node.instanceId })[0]
    }
    if ($current.State.Name -eq 'stopped') {
        Write-Host "Starting $role ($($node.instanceId))"
        Invoke-LabAws -Config $c -AwsArguments @('ec2','start-instances','--instance-ids',$node.instanceId) | Out-Null
    } elseif ($current.State.Name -notin @('pending','running')) {
        throw "Refusing unexpected state for ${role}: $($current.State.Name)"
    }
    Invoke-LabAws -Config $c -AwsArguments @('ec2','wait','instance-running','--instance-ids',$node.instanceId) | Out-Null
    Invoke-LabAws -Config $c -AwsArguments @('ec2','wait','instance-status-ok','--instance-ids',$node.instanceId) | Out-Null
}
Show-LabInventory -Config $c
Write-Host 'EC2 checks passed. Verify k3s, ZeekControl and application health separately. No mirroring session was created.'
