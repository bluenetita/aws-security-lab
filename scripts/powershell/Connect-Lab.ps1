#requires -Version 5.1
[CmdletBinding()]
param([Parameter(Mandatory=$true)][ValidateSet('control-plane','worker','zeek')][string]$Role,
      [string]$ConfigPath)
. (Join-Path $PSScriptRoot 'Common.ps1')
$c = Read-LabConfig -ConfigPath $ConfigPath
Assert-LabAccount -Config $c
$publicIp = Get-NodePublicIp -Config $c -Role $Role
$options = @(Get-LabSshArguments -Config $c -Role $Role)
$destination = "$($c.ssh.user)@$publicIp"
Write-Host "Connecting to $Role at $publicIp. Verify the host fingerprint if prompted."
& ssh @options $destination
if ($LASTEXITCODE -ne 0) { throw 'SSH failed. Check current source IP, Security Group, key and host identity; do not disable security checks.' }
