# BlueGuard release roadmap

Status as of the final 24 November 2026 checkpoint. Future version identifiers and sequence are planning decisions, not guaranteed delivery dates.

| Release / milestone | Scope | Status |
|---|---|---|
| v0.5.0-rc1 | Snapshot freshness | Implemented in deployed lineage |
| v0.5.0-rc2 | Publisher heartbeat monitoring | Implemented in deployed lineage |
| v0.5.0-rc3 | Ingestion receipt and freshness | Implemented; rollback image retained |
| v0.5.0-rc4 | Telemetry Quality Gate, API and dashboard | Deployed; 54 tests passed; Canary removed |
| v0.5.0-rc5 | AWS CloudWatch metrics and mirroring inventory | **Planned, not implemented** |
| v0.5.0 | Stable lab release | Planned: source sync, reproducible build, hardening and validation |
| v0.6.0 | Detection engine | Planned, no validated detection capability yet |

## rc5 acceptance criteria (proposed)

- Verify EC2 source instance/ENI, monitoring mode, current mirror-session inventory and actual CloudWatch response shape. Historical metric data may be used before enabling new test sessions.
- Collect byte and packet metrics (`NetworkMirrorIn/Out`, `NetworkSkipMirrorIn/Out`, `NetworkPacketsMirrorIn/Out`, `NetworkPacketsSkipMirrorIn/Out`) with explicit source, period and timestamps; verify actual availability and units against AWS documentation and the lab response.
- Keep AWS collection separate from FastAPI; use approved IAM least privilege and no persistent credentials in the app or repository. Use validated bounded JSON and atomic publication.
- Distinguish observed zero skips, positive skips, missing/partial datapoints, authorization errors, stale metrics and absent current session. Do not infer historical session state from current inventory.
- Add a read-only API and dashboard panel before extending the Quality Gate. Do not sum AWS skipped bytes and Zeek `missed_bytes` or suppress security alerts.
- Add tests, run regression suite, build and validate an isolated Canary; retain rollback and confirm cleanup.

Before stable release: synchronize the real rc4+ source and manifests, review dependency/image provenance, implement appropriate network policies and access controls, improve snapshot consistency and perform timed full-path and recovery tests. The scope remains a lab until the required production controls and evidence exist.
