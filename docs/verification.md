# Verification matrix and read-only checks

## Observed validation

| Layer | Test | Result | Evidence |
|---|---|---|---|
| Mirror/Zeek | HTTP smoke test | 3/3 HTTP 200 + Zeek records | `evidence/2026-11-16/` |
| Mirror/Zeek | LIVE-AD-03 and -04 | CloudWatch skips and Zeek gaps quantified | `evidence/2026-11-18/result.json` |
| Mirror/Zeek | LIVE-AD-05 | UID identified; `missed_bytes=0` on connection | `evidence/2026-11-19/result.json` |
| Ingestion | Repeated event | 1 new, then 1 duplicate, 1 total | `evidence/2026-11-19/result.json` |
| Collector | Python tests | 8/8 pass | Test output recorded; source not bundled |
| Collector | SSH retry | Checkpoint unchanged on failure, successful recovery | Recorded host test output |
| Collector | Rotation | Incomplete line and gzip rotation scenario passed | Mock test; not equivalent to in-service rotation |
| Publisher | Scheduled run and file permissions | Successful timer run, mode 0440, API access | Host test output |
| Kubernetes | Deployment rollout | `1/1 Running`, 0 restarts, v0.4.2-lab | `evidence/2026-11-19/result.json` |
| Dashboard | Synthetic fixture update | 3 API/UI records in preview | Screenshot/API observation |
| Historical v0.2.0 source snapshot | Local API regression suite: **7/7 passed** (earlier archive verification) | Historical report only; not a rerun of the current v0.4.2 tree or rc4 |
| rc4 application QA | 37 existing + 14 backend + 3 UI smoke tests | **54/54 pass**, 1 warning; final version test 1.14 s | `evidence/2026-11-24/result.json` |
| rc4 image | Source checksums, runtime identity, OpenAPI | 24/24 SHA-256; UID 10001; 6 required GET routes | Same evidence |
| rc4 Canary | Separate selector, rollout, seven HTTP endpoints | Pass; Service retained rc3 endpoint only | Same evidence |
| rc4 main | Rolling update, seven HTTP endpoints, release assertion | Pass; version rc4; 1/1 Ready, zero restarts after cleanup | Same evidence |
| rc4 quality policy | Stored snapshot and component health | `degraded`, `gaps_observed`; stale snapshot/ingestion, healthy publisher | Same evidence |
| rc4 browser | Visual check reported; manual refresh/network request not independently confirmed | Partial functional coverage | Conversation report; no browser automation results bundled |
| Fresh end-to-end event | New mirrored UID → browser with measured latency | No complete timed rc4 trace retained | Stored batch and API observations only |
| Wazuh integration | End-to-end Wazuh → BlueGuard | **Not implemented** | No evidence |

## Kubernetes checks (Control Plane)

Read-only commands to execute on the **Control Plane EC2**, after confirming the VM is running:

```bash
sudo systemctl is-active k3s
sudo k3s kubectl get nodes -o wide
sudo k3s kubectl -n blueguard get deployments,pods,services -o wide
sudo k3s kubectl -n blueguard rollout status deployment/blueguard-api --timeout=120s
sudo k3s kubectl -n blueguard logs deployment/blueguard-api --tail=30
```

API health via the running container, without opening an external port:

```bash
sudo k3s kubectl -n blueguard exec deployment/blueguard-api -- \
  python -B -c 'import json,urllib.request; b="http://127.0.0.1:8080"; print(json.load(urllib.request.urlopen(b+"/api/v1/status",timeout=5))); print(json.load(urllib.request.urlopen(b+"/api/v1/zeek/connections",timeout=5))["total"])'
```

## Collector and publisher checks

**Zeek sensor:**

```bash
sudo /opt/zeek/bin/zeekctl status
systemctl is-active blueguard-zeek-collector.timer
systemctl list-timers --all blueguard-zeek-collector.timer
sudo journalctl -u blueguard-zeek-collector.service -n 25 --no-pager
```

**Control Plane:**

```bash
systemctl is-active blueguard-zeek-publisher.timer
systemctl list-timers --all blueguard-zeek-publisher.timer
sudo journalctl -u blueguard-zeek-publisher.service -n 25 --no-pager
sudo stat -c '%a %U:%G %s %n' /var/lib/blueguard/zeek/conn-ingested.jsonl
```

A successful `oneshot` service may appear `inactive (dead)` between scheduled runs. Inspect its exit status and journal rather than treating that state alone as a failure.

**No commands in this document modify runtime resources.** To start/stop EC2 or create mirroring, follow change-control procedures and [operations](operations.md).

## rc4 Service and Quality Gate checks

On the Control Plane, retrieve the Service IP and query the deployed API without opening a public port:

```bash
SERVICE_IP=$(sudo -n k3s kubectl -n blueguard get svc blueguard-api -o jsonpath='{.spec.clusterIP}')
curl -fsS --max-time 10 "http://$SERVICE_IP/api/v1/status" | jq -e '.version == "0.5.0-rc4"'
curl -fsS --max-time 10 "http://$SERVICE_IP/api/v1/telemetry/quality" | jq .
sudo -n k3s kubectl -n blueguard get pods -o wide
sudo -n k3s crictl images | grep -E 'blueguard-api.*0\.5\.0-rc[34]'
```

A non-healthy quality state is not automatically a failed deployment. Verify that reasons and component values match the policy, and keep unknown connectivity distinct from health/readiness. The commands above are read-only. The 54-test result refers to the EC2 development tree; this documentation update did not run the suite again.
