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
| Historical v0.2.0 source snapshot | Local API regression suite: **7/7 passed** (earlier archive verification) | Historical report only; not a rerun of the consolidated rc4 tree |
| rc4 application QA | 37 existing + 14 backend + 3 UI smoke tests | **54/54 pass**, 1 warning; final version test 1.14 s | `evidence/2026-11-24/result.json` |
| rc4 image | Source checksums, runtime identity, OpenAPI | 24/24 SHA-256; UID 10001; 6 required GET routes | Same evidence |
| rc4 Canary | Separate selector, rollout, seven HTTP endpoints | Pass; Service retained rc3 endpoint only | Same evidence |
| rc4 main | Rolling update, seven HTTP endpoints, release assertion | Pass; version rc4; 1/1 Ready, zero restarts after cleanup | Same evidence |
| rc4 quality policy | Stored snapshot and component health | `degraded`, `gaps_observed`; stale snapshot/ingestion, healthy publisher | Same evidence |
| rc4 browser | Visual check reported; manual refresh/network request not independently confirmed | Partial functional coverage | Conversation report; no browser automation results bundled |
| Fresh end-to-end event | New mirrored UID → browser with measured latency | No complete timed rc4 trace retained | Stored batch and API observations only |
| Wazuh integration | End-to-end Wazuh → BlueGuard | **Not implemented** | No evidence |

## Consolidated repository CI

The project owner reports that **BlueGuard CI run #3** succeeded on commit
`caa8ce1` (`chore/consolidate-blueguard-rc4`) in **36 seconds**. This record is
based on the supplied run results; the GitHub Actions run was not queried or
rerun for this documentation update.

| Check | Reported result | Scope |
|---|---|---|
| Regression suite | **54 passed, 1 warning in 0.54 seconds** | Consolidated application source at `caa8ce1`; the warning is a `StarletteDeprecationWarning` concerning `httpx` and `TestClient`. |
| Source integrity manifest | **143 canonical Git checksums verified** | Indexed source at `caa8ce1`. |
| QA container build | Successful | Repository CI build, not a deployment. |
| Application container build | Successful | Repository CI build, not a published image or a reproducibility test. |
| Kustomize | Rendering and configured baseline checks successful | Control-plane lab overlay; no apply or fresh deployment test. |

CI run #2 failed because tests were excluded from the Docker build context.
`applications/blueguard-api/Dockerfile.test.dockerignore` resolved that issue,
according to the project owner. The deprecation warning remains technical
debt. Run #3 validates the application baseline at `caa8ce1`; it does not
validate later documentation changes, the recovered host pipeline or Zeek
policies, reproducible provisioning, bit-for-bit image reproducibility, or a
fresh end-to-end AWS trace.

## M3.3 host pipeline source verification (26 November 2026)

The project owner reports that prior BlueGuard CI run #5 succeeded (36-second
workflow, 32-second job) on the previously published baseline. Its logs were
not independently inspected here, and it did not run the new host suite.
The edited workflow adds that suite on `ubuntu-24.04` after the manifest check,
with path filters for host sources and tests. Remote CI validation of this
revision remains pending.

From the repository root, the local standard-library suite ran with:

```text
wsl --exec python3 -B -m unittest discover -s tests/host_pipeline -p 'test_*.py' -v
```

The fresh M3.3f WSL Python 3.12.3 run recorded **41 tests passed** in
**0.405 seconds**, zero failures and zero expected failures; the earlier
M3.3e run passed in 0.383 seconds. Tests use synthetic JSONL, temporary
directories and mocked transport; they do not verify live SSH, root-owned
service paths, systemd operation, Zeek policy loading, or an end-to-end trace.
The project owner separately reports independent collector testing of
**21/21 passed** on Linux Python 3.13.5 and five additional passing boundary
experiments. Those checks overlap the local suite and are not an additive
test count. Local YAML parsing and Bash syntax checks passed; independent
synthetic checks of the CI step's success, failure and zero-test behavior were
reported by the project owner.

The tests reproduce and guard against BG-BUG-001 (truncation/refill skips),
BG-BUG-002 (masked `FileNotFoundError`), BG-BUG-001a (buffered continuity
reads), and BG-BUG-001b (lost continuity evidence during multi-batch ACKs).
The collector uses a persisted 4096-byte SHA-256 anchor and checks all bytes
read for the pending batch before delivery and after ACK. A failed post-ACK
check leaves the last persisted checkpoint in place; the receiver may have
accepted the batch, so recovery replays it and depends on deduplication.
These source-level checks do not establish exactly-once delivery or complete
capture. See [architecture](architecture.md) and [limitations](limitations.md).

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

A non-healthy quality state is not automatically a failed deployment. Verify that reasons and component values match the policy, and keep unknown connectivity distinct from health/readiness. The commands above are read-only. The earlier rc4 application QA row refers to the EC2 development tree; the separate consolidated repository CI result above refers to `caa8ce1`. This documentation update did not run the suite again.
