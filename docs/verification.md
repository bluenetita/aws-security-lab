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

The project owner subsequently reports GitHub Actions run `45812342775`
completed successfully in **30 seconds** on commit
`906a8653b4bf6a03cf13660517c8e915f2b1b467`, the committed M3.3 host
pipeline and CI revision. Detailed per-step host/application test counts and
logs remain unverified in this offline documentation task. The run does not
cover the later M3.4 Zeek policy changes; the Zeek regression suite is
not yet integrated into CI.

## M3.3 host pipeline source verification (26 November 2026)

The project owner reports that prior BlueGuard CI run #5 succeeded (36-second
workflow, 32-second job) on the previously published baseline. Its logs were
not independently inspected here, and it did not run the new host suite.
The committed workflow adds that suite on `ubuntu-24.04` after the manifest
check, with path filters for host sources and tests. Run `45812342775` is
reported successful on this revision; its detailed test output was not
independently inspected here.

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

## M3.4 offline Zeek policy verification (26 November 2026)

The local runtime is `/opt/zeek/bin/zeek` **9.0.1** in Ubuntu 24.04.1 WSL2
(amd64), with Python 3.12.3 as a non-root user. The persistent suite is under
`tests/zeek_policy/`; it uses isolated temporary directories, controlled
synthetic timestamps, direct event injection and generated offline PCAPs. It
does not capture live traffic, contact a sensor or use operational logs.

Before the BG-BUG-003 correction, the normal suite passed **39/39** tests, but
two separate host/destination acceptance tests failed: after 80 synthetic
minutes, a new identity still received `capacity_exceeded`. The corrected
policy and suite now include those cases in normal discovery. The M3.4f local
run executed:

```bash
python3 -B -m unittest discover -s tests/zeek_policy -p 'test_*.py' -v
python3 -B -m unittest discover -s tests/host_pipeline -p 'test_*.py' -v
```

The Zeek suite passed **59/59** and host suite **41/41**, each with zero
failures, skips and expected failures. The added regression confirms that an
identity with one confirmed sample expires with an audit reporting that
history, then returns with zero prior samples and learns again on its next
callback. That focused fixture uses a **120-second TTL** and immediate
learning only to expose the history transition; the policy default remains
60 minutes with delayed learning enabled. The suite also covers eligibility,
thresholds, callback ordering, pending discard, independent scopes, capacity
recovery, source-wide holds, invalid TTL, six representative native JSON log
schemas and the synthetic packet-to-policy path. See the
[test README](../tests/zeek_policy/README.md) for fixture provenance and exact
scope.

The `data_exfil_baseline` native JSON key set is unchanged. For a commit,
`ts` is the confirmation tick, `original_sample_ts` is its sample-window
time, and count/bytes describe that sample. For the existing aggregate
discard event, `ts` and `original_sample_ts` are both discard time; count and
bytes describe pending samples discarded. For
`exfil_baseline_profile_expired`, `ts` is the expiration tick,
`original_sample_ts` is the last observed active-window time, and count/bytes
describe confirmed history retired. Pending samples produce a separate
discard record before the expiration record and are never confirmed by
expiration.

These are local synthetic and offline packet tests, not CI results or proof of
real-world detection efficacy. Capture completeness, default-limit memory and
performance, live service behavior and a timed end-to-end AWS trace remain
unverified.

## M3 final evidence and offline M4 disposition (26 November 2026)

The **last verified implementation baseline** is
`a2fee23329776d735060473d59d681ef2de07ea5` on
`chore/consolidate-blueguard-rc4`. Local Git and the previous M3.4h read-only
remote check agreed on that SHA; the tree and index were clean. The committed
manifest and the index at this review passed **161/161** canonical checksums.

| M3 area | Attributable result | Boundary |
| --- | --- | --- |
| M3.1 source integrity and CI | 161/161 local manifest; GitHub Actions [run #7](https://github.com/bluenetita/aws-security-lab/actions/runs/45845763503) completed successfully in 27 seconds on `a2fee23`. | Prior M3.4h public API inspection verified push event, SHA and successful manifest, host, application, QA build, image build and Kustomize steps. Job logs returned HTTP 403, so actual CI test counts and skip/failure details remain unverified. |
| M3.2 local validation environment | Ubuntu 24.04.1 WSL2, Python 3.12.3 and Zeek 9.0.1, non-root. | Local offline environment, not the deployed sensor. |
| M3.3 host pipeline | 41/41 local tests passed; BG-BUG-001, BG-BUG-001a, BG-BUG-001b and BG-BUG-002 are covered within synthetic regression scope. | The CI host step succeeded, but its actual test count is unavailable; live service and exactly-once behavior remain unverified. |
| M3.4 Zeek policy | 59/59 local offline tests passed; BG-BUG-003 host/destination capacity recovery and baseline lifecycle are covered. | The Zeek suite is versioned but absent from CI; synthetic results do not establish live detection efficacy. |

The historical rc4 application count of 54, the 41 host tests and the 59
Zeek tests are separate evidence sets, not one verified 154-test execution.
No corrected collector or Adaptive policy deployment to AWS has been verified.
The M3 readiness decision is **CONDITIONAL GO for offline M4 contract and
fixture development**. There is no live dependency for that design work;
live integration and production release have separate gates in
[limitations](limitations.md) and the [product roadmap](product/PRODUCT_ROADMAP.md).
The documentation closeout still requires an authorized commit and
publication. No M4 implementation has started.

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

A non-healthy quality state is not automatically a failed deployment. Verify that reasons and component values match the policy, and keep unknown connectivity distinct from health/readiness. The commands above are read-only. The earlier rc4 application QA row refers to the EC2 development tree; the separate consolidated repository CI result above refers to `caa8ce1`. This M3.4 documentation update ran the Zeek and host suites, not the application QA suite.
