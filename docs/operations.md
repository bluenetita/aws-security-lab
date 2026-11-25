# Laboratory operations

**Audience:** authorized operators of the AWS experiment. Commands that start EC2 or delete Traffic Mirroring sessions **modify AWS resources and may affect billing or monitoring**. Verify account, region, instance IDs and scope before execution.

## Configuration

Scripts under [`scripts/powershell/`](../scripts/powershell/) use `.local/lab-state.json`, which is **not tracked**. Copy and adapt [`config/lab.example.json`](../config/lab.example.json), providing approved AWS account and instance identifiers locally. Original start/stop helper scripts cover **Control Plane, Worker and Zeek only**; they do not manage Wazuh.

Do not commit `.local/`, SSH keys, AWS credentials or kubeconfig files.

## EC2 inventory (Windows PowerShell)

```powershell
$Profile = 'YOUR_AWS_PROFILE'
$Region = 'eu-south-1'
$InstanceIds = @('i-REPLACE_CONTROL_PLANE', 'i-REPLACE_WORKER', 'i-REPLACE_ZEEK', 'i-REPLACE_WAZUH')

aws sts get-caller-identity --profile $Profile
aws ec2 describe-instances --profile $Profile --region $Region `
  --instance-ids $InstanceIds `
  --query 'Reservations[].Instances[].{ID:InstanceId,State:State.Name,PrivateIP:PrivateIpAddress}' `
  --output table
```

The sample instance IDs are placeholders. Do not execute a start/stop command until replaced with validated IDs.

## Starting an existing subset

```powershell
# Choose only the approved instances required for this test.
$ToStart = @('i-REPLACE_CONTROL_PLANE', 'i-REPLACE_ZEEK')
aws ec2 start-instances --profile $Profile --region $Region --instance-ids $ToStart
aws ec2 wait instance-status-ok --profile $Profile --region $Region --instance-ids $ToStart
```

After start, verify k3s, Pod readiness, timers and Zeek (see [verification](verification.md)). EC2 `running` is not proof that an application is healthy. Public IP addresses can change after stop/start.

## Traffic Mirroring inspection and cleanup

```powershell
aws ec2 describe-traffic-mirror-sessions --profile $Profile --region $Region --output json
```

Delete **only an identified, approved test session**, after confirming its source ENI and target:

```powershell
$SessionId = 'tms-REPLACE_APPROVED_TEST_SESSION'
aws ec2 describe-traffic-mirror-sessions --profile $Profile --region $Region `
  --traffic-mirror-session-ids $SessionId --output json

# DESTRUCTIVE FOR MONITORING: ends packet copying for that session.
aws ec2 delete-traffic-mirror-session --profile $Profile --region $Region `
  --traffic-mirror-session-id $SessionId

aws ec2 describe-traffic-mirror-sessions --profile $Profile --region $Region --output json
```

Session deletion is separate from deleting target/filter resources, which may be reused. Never treat a failed `describe` call as evidence of an empty session list.

## Graceful shutdown

```powershell
# Only after Traffic Mirroring cleanup has been verified.
aws ec2 stop-instances --profile $Profile --region $Region --instance-ids $InstanceIds
aws ec2 wait instance-stopped --profile $Profile --region $Region --instance-ids $InstanceIds
aws ec2 describe-instances --profile $Profile --region $Region `
  --instance-ids $InstanceIds `
  --query 'Reservations[].Instances[].{ID:InstanceId,State:State.Name}' --output table
```

Stopping EC2 avoids normal instance-compute charges but does not remove EBS or other billable resources. **Last recorded verification:** all four lab EC2 instances `stopped` and no traffic-mirror sessions, as captured by AWS CLI. This does not establish their present state.

## Dashboard access

The tested deployment used a `ClusterIP` Service and SSH forwarding. Determine the current ClusterIP from Kubernetes; do **not** assume it is unchanged:

```bash
# Control Plane
sudo k3s kubectl -n blueguard get service blueguard-api -o wide
```

Example command from Windows PowerShell, with variables confirmed for the active lab:

```powershell
$PublicIp = 'REPLACE_CURRENT_CONTROL_PLANE_PUBLIC_IP'
$ServiceIp = 'REPLACE_CURRENT_CLUSTER_IP'
$PrivateKey = "$HOME\.ssh\REPLACE_APPROVED_KEY"
ssh -N -i $PrivateKey -o IdentitiesOnly=yes -o ExitOnForwardFailure=yes `
  -L "127.0.0.1:18083:${ServiceIp}:80" "ubuntu@${PublicIp}"
```

Open `http://127.0.0.1:18083` while the SSH window remains open. This is an administrative lab-access method; it is not end-user authentication.

## rc4 release and rollback (Control Plane)

The rc4 image is node-local, with `imagePullPolicy: Never`; both rc3 and rc4 were retained in containerd at the final check. The main `blueguard-api` Deployment in namespace `blueguard` was 1/1 Ready with zero restarts, and the `blueguard-api-canary` Deployment was deleted. Verify current image availability and workload state before any change. Do not apply the older repository manifests as a replacement for rc4.

```bash
sudo -n k3s kubectl -n blueguard get deployments,pods,services -o wide
sudo -n k3s kubectl -n blueguard rollout history deployment/blueguard-api
sudo -n k3s crictl images | grep -E 'blueguard-api.*0\.5\.0-rc[34]'
```

**Change control:** only if a rollback is required and authorized, after confirming the rc3 image and control-plane placement:

```bash
sudo -n k3s kubectl -n blueguard set image deployment/blueguard-api \
  api=localhost/blueguard-api:0.5.0-rc3
sudo -n k3s kubectl -n blueguard rollout status deployment/blueguard-api --timeout=120s
```

Verify readiness and `/api/v1/status` afterward. Rollback is an available procedure, not a rollback execution verified for this release. `sudo -n` fails rather than prompting for a password. The rc4 release did not require changing sudo policy or passwords.

**End-of-day checkpoint:** the final application observation was at 18:41:45 UTC on 24 November. No subsequent AWS shutdown or mirror-session inventory was supplied. Close any local tunnel/port-forward when finished; independently check authorized AWS resources and clean up approved test sessions before stopping instances. The earlier shutdown evidence remains historical.
