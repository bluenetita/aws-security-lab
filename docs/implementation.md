# Implemented components

## Collector on the Zeek sensor

- Program installed at `/usr/local/libexec/blueguard-zeek-collector`.
- Reads new records from `/opt/zeek/logs/current/conn.log` and rotated gzip archives.
- Persists progress in `/var/lib/blueguard-sender/state/state.json`.
- Handles incomplete lines, already-completed archives, batching and failed SSH transfers; checkpoint advances after acknowledgment.
- Executes as dedicated `blueguard-sender` with permission to read Zeek logs; does not require a login shell.

**Timer scheduling (on Zeek):**

```ini
[Timer]
OnBootSec=2min
OnUnitInactiveSec=1min
AccuracySec=10s
```

The execution interval is approximately one minute **after completion of the previous oneshot run**, with timer scheduling tolerances. It is not a continuously running daemon.

## Restricted SSH receiver on Control Plane

- SSH public-key authentication with a dedicated Ed25519 key; host identity checked through pinned `known_hosts`.
- Receiving account `blueguard-ingest`, restricted in `authorized_keys` with `from`, `restrict` and `command=/usr/local/libexec/blueguard-ssh-receiver`.
- Allowed operations: limited `health` and `ingest` workflow; arbitrary command execution rejected in tests.
- Validates JSONL, uses file locks and atomic replacement, deduplicates `(uid, ts)`.
- Private store `/var/lib/blueguard-ingest/incoming/conn.jsonl`, file mode `0600`.
- Observed limits: **1 MiB per batch**, **10 MiB** and **10,000 records** globally.

## Publisher on Control Plane

- Program `/usr/local/libexec/blueguard-zeek-publisher` is a hardened `systemd` oneshot service, reading the private receiver store.
- Atomically writes `/var/lib/blueguard/zeek/conn-ingested.jsonl` with mode `0440`, owner `root`, group `10001`.
- Avoids unnecessary replacement when the content is unchanged; published content validated and compared to receiver data.

**Timer scheduling (on Control Plane):**

```ini
[Timer]
OnCalendar=minutely
AccuracySec=10s
Persistent=true
```

Calendar scheduling occurs approximately each minute. `Persistent=true` supports catch-up when a scheduled invocation was missed while the timer was inactive; it does not guarantee replay of every missed minute.

## Kubernetes application

The deployed v0.4.2-lab instance consists of one `blueguard-api` Deployment, one containerized Pod and one private `ClusterIP` Service in namespace `blueguard`. FastAPI serves both REST endpoints and the static HTML/CSS/JavaScript files; **there is no separate frontend Pod**.

The runtime mounts the published Zeek directory read-only under `/app/data/zeek`. API file-loading logic uses filesystem metadata to invalidate cached data after an atomic file update. The browser polls Zeek data every 30 seconds when its view is visible and the tab is active.

| Endpoint | Observed behavior |
|---|---|
| `/healthz` | HTTP OK and status `ok` |
| `/readyz` | HTTP OK and status `ready` |
| `/api/v1/status` | `version=0.4.2-lab` |
| `/api/v1/zeek/connections` | One observed LIVE-AD-05 record; `live=false` |

`live=false` is an intentional distinction between polling/snapshot data and direct streaming. Legacy fields such as `source=zeek_snapshot` and `zeek_connected=false` need clearer semantics in a future API version.

## Source-artifact boundary

The v0.4.2 collector, receiver, publisher, API changes, unit files and deployment manifest are **not completely present in this archive**; they were installed and validated on the EC2 hosts. This document describes observed execution, **not a complete installable v0.4.2 release**. See [source availability](source-availability.md).
