# Laboratory helper scripts

These are **optional historical helpers**, not a deployment automation system. They use Windows PowerShell 5.1+, AWS CLI v2 and OpenSSH. They were not validated against an active AWS account as part of this repository curation.

| Script | Function |
|---|---|
| `powershell/Show-Lab.ps1` | Read-only EC2 and mirror inventory |
| `powershell/Start-Lab.ps1` | Preview or start selected existing instances (`-Apply`) |
| `powershell/Stop-Lab.ps1` | Preview or stop three configured instances (`-Apply`) |
| `powershell/Connect-Lab.ps1` | SSH to a selected host |
| `powershell/Open-BlueGuardTunnel.ps1` | SSH forwarding to private Kubernetes Service |
| `linux/check-zeek.sh` | Local Zeek status inspection |
| `linux/http-probe.sh` | Generates controlled HTTP test requests |

**Coverage:** original start/stop helpers manage Control Plane, Worker and Zeek; they **do not** include Wazuh. They require an approved, locally populated `.local/lab-state.json`, excluded from version control. See [`config/lab.example.json`](../config/lab.example.json).

Mutation commands must be reviewed before use. `Start-Lab` can resume EC2 charges; `Stop-Lab` does not delete active mirror sessions. See [operations and cleanup](../docs/operations.md).
