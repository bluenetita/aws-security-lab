#requires -Version 5.1
# Retrieves public EC2 IP and ClusterIP at runtime. No public application exposure.
[CmdletBinding()]
param([string]$ConfigPath,[ValidateRange(1024,65535)][int]$LocalPort=18080)
. (Join-Path $PSScriptRoot 'Common.ps1')
$c = Read-LabConfig -ConfigPath $ConfigPath
Assert-LabAccount -Config $c
$publicIp = Get-NodePublicIp -Config $c -Role 'control-plane'
$options = @(Get-LabSshArguments -Config $c -Role 'control-plane')
$destination = "$($c.ssh.user)@$publicIp"
# Static command: no shell interpolation of untrusted resource names.
$remoteCommand = 'sudo -n k3s kubectl get service blueguard-api -n blueguard -o json'
$lines = @(& ssh @options $destination $remoteCommand)
if ($LASTEXITCODE -ne 0) { throw 'Cannot query the Kubernetes Service over SSH; no tunnel opened.' }
try { $service = ($lines -join "`n") | ConvertFrom-Json }
catch { throw 'Invalid Service JSON returned by kubectl.' }
if ($service.spec.type -ne 'ClusterIP') { throw 'Expected a private ClusterIP Service. Review configuration.' }
$clusterIp = [string]$service.spec.clusterIP
$address = $null
if (-not [System.Net.IPAddress]::TryParse($clusterIp,[ref]$address) -or
    $address.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork) {
    throw 'Expected an IPv4 ClusterIP.'
}
$ports = @($service.spec.ports | Where-Object { $_.name -eq 'http' })
if ($ports.Count -ne 1 -or [int]$ports[0].port -ne 80) { throw 'Unexpected HTTP Service port; review before forwarding.' }
$forward = "127.0.0.1:${LocalPort}:${clusterIp}:80"
Write-Host "Dashboard: http://127.0.0.1:$LocalPort/"
Write-Host "Destination queried live: $publicIp -> ${clusterIp}:80. Keep this window open; Ctrl+C closes the tunnel."
& ssh @options -o ExitOnForwardFailure=yes -N -L $forward $destination
if ($LASTEXITCODE -ne 0) { throw 'Tunnel failed or disconnected. Do not start another on the same port until checking the existing listener.' }
