# Shared helpers. Requires Windows PowerShell 5.1+, AWS CLI v2 and OpenSSH.
# No credentials, private keys or public EC2 addresses are stored here.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Read-LabConfig {
    param([string]$ConfigPath)
    if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
        $repoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
        $ConfigPath = Join-Path $repoRoot '.local/lab-state.json'
    }
    if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
        throw "Missing config: $ConfigPath. See docs/operations.md and config/lab.example.json; do not store credentials in this file."
    }
    $config = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
    if ($config.schemaVersion -ne 1) { throw 'Unsupported config schema.' }
    if ($config.expectedAccountId -notmatch '^\d{12}$') { throw 'Set expectedAccountId to the approved AWS account ID.' }
    if ($config.vpcId -notmatch '^vpc-[0-9a-f]+$') { throw 'Invalid VPC ID.' }
    if ([string]::IsNullOrWhiteSpace($config.profile) -or [string]::IsNullOrWhiteSpace($config.region)) {
        throw 'Missing AWS profile or region.'
    }
    foreach ($role in @('control-plane','worker','zeek')) {
        $nodes = @($config.nodes | Where-Object { $_.role -eq $role })
        if ($nodes.Count -ne 1 -or $nodes[0].instanceId -notmatch '^i-[0-9a-f]+$') {
            throw "Expected one configured instance ID for role $role."
        }
    }
    if (@($config.nodes | Select-Object -ExpandProperty instanceId -Unique).Count -ne 3) {
        throw 'Instance IDs must be distinct.'
    }
    Get-Command aws -ErrorAction Stop | Out-Null
    return $config
}

function Invoke-LabAws {
    param([Parameter(Mandatory=$true)]$Config,
          [Parameter(Mandatory=$true)][string[]]$AwsArguments)
    $allArguments = @($AwsArguments) + @('--profile', [string]$Config.profile,
        '--region', [string]$Config.region, '--output', 'json', '--no-cli-pager')
    # Do not redirect stderr into JSON. A failed AWS command is never an empty inventory.
    $lines = @(& aws @allArguments)
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        throw "AWS CLI failed ($code): $($AwsArguments -join ' '). Read the AWS error; no automatic retry or mutation."
    }
    $text = $lines -join "`n"
    if ([string]::IsNullOrWhiteSpace($text)) { return $null }
    try { return ($text | ConvertFrom-Json) }
    catch { throw "Unexpected AWS output: not JSON for $($AwsArguments -join ' ')." }
}

function Assert-LabAccount {
    param($Config)
    $identity = Invoke-LabAws -Config $Config -AwsArguments @('sts','get-caller-identity')
    if ($identity.Account -ne $Config.expectedAccountId) {
        throw "Wrong AWS account. Expected $($Config.expectedAccountId), received $($identity.Account)."
    }
    Write-Host "AWS account verified; profile=$($Config.profile), region=$($Config.region)"
}

function Get-LabNode {
    param($Config,[string]$Role)
    $nodes = @($Config.nodes | Where-Object { $_.role -eq $Role })
    if ($nodes.Count -ne 1) { throw "Unknown or duplicated role: $Role" }
    return $nodes[0]
}

function Get-LabInstances {
    param($Config)
    $ids = @($Config.nodes | ForEach-Object { [string]$_.instanceId })
    $result = Invoke-LabAws -Config $Config -AwsArguments (@('ec2','describe-instances','--instance-ids') + $ids)
    $instances = @($result.Reservations | ForEach-Object { $_.Instances })
    if ($instances.Count -ne $ids.Count) { throw 'AWS did not return all configured instances.' }
    foreach ($instance in $instances) {
        $node = @($Config.nodes | Where-Object { $_.instanceId -eq $instance.InstanceId })
        if ($node.Count -ne 1 -or $instance.VpcId -ne $Config.vpcId) {
            throw "Instance/VPC mismatch for $($instance.InstanceId)."
        }
        if ($instance.PrivateIpAddress -ne $node[0].privateIp) {
            throw "Unexpected private IP for $($instance.InstanceId). Inspect the inventory before continuing."
        }
    }
    return $instances
}

function Get-LabMirrors {
    param($Config)
    $result = Invoke-LabAws -Config $Config -AwsArguments @('ec2','describe-traffic-mirror-sessions',
        '--filters', "Name=network-interface-id,Values=$($Config.mirror.sourceEniId)")
    return $result.TrafficMirrorSessions
}

function Show-LabInventory {
    param($Config)
    $instances = @(Get-LabInstances -Config $Config)
    $rows = foreach ($node in $Config.nodes) {
        $instance = @($instances | Where-Object { $_.InstanceId -eq $node.instanceId })[0]
        $publicIp = $null
        if ($null -ne $instance.PSObject.Properties['PublicIpAddress']) {
            $publicIp = $instance.PublicIpAddress
        }
        [PSCustomObject]@{Role=$node.role;Instance=$instance.InstanceId;
            State=$instance.State.Name;PrivateIP=$instance.PrivateIpAddress;PublicIP=$publicIp}
    }
    $rows | Format-Table -AutoSize
}

function Get-NodePublicIp {
    param($Config,[string]$Role)
    $node = Get-LabNode -Config $Config -Role $Role
    $instances = @(Get-LabInstances -Config $Config)
    $instance = @($instances | Where-Object { $_.InstanceId -eq $node.instanceId })[0]
    if ($instance.State.Name -ne 'running') { throw "$Role is not running. Use Start-Lab.ps1 deliberately." }
    if ($null -eq $instance.PSObject.Properties['PublicIpAddress']) { throw "No public IPv4 for $Role; do not open more ports." }
    $address = $null
    if (-not [System.Net.IPAddress]::TryParse([string]$instance.PublicIpAddress,[ref]$address) -or
        $address.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork) {
        throw "Invalid public IPv4 for $Role."
    }
    return [string]$instance.PublicIpAddress
}

function Get-LabSshArguments {
    param($Config,[string]$Role)
    Get-Command ssh -ErrorAction Stop | Out-Null
    $key = Join-Path $HOME ([string]$Config.ssh.privateKeyRelativeToHome)
    if (-not (Test-Path -LiteralPath $key -PathType Leaf)) { throw "SSH private key not found: $key. Never copy it into the repository." }
    $node = Get-LabNode -Config $Config -Role $Role
    # Stable host identity across changing public IPs. Verify fingerprint on first use.
    return @('-i',$key,'-o','IdentitiesOnly=yes','-o',"HostKeyAlias=$($node.instanceId)",
        '-o','ServerAliveInterval=30','-o','ServerAliveCountMax=3','-o','ConnectTimeout=15')
}
