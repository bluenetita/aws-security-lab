# Changelog

This changelog records changes to repository artifacts and verified technical milestones; documentation edits are not described as deployments.

## 2026-11-20 — Repository documentation curation

- Replaced personal working notes and meeting-specific material with technical architecture, experimental measurements, test matrix, security controls, limitations and operations documentation.
- Removed obsolete duplicate status snapshots and historical instructions that described LIVE-AD-05 as merely planned.
- Preserved v0.2.0 application source, historical infrastructure examples and structured laboratory evidence without claiming that v0.4.2 source was included.
- Regenerated the file-integrity manifest. **No EC2, Kubernetes or application runtime changes were made as part of this archive revision.**

## 2026-11-19 — Verified laboratory milestones

- LIVE-AD-05: controlled 5 MiB HTTP upload at 32 KiB/s, Zeek `missed_bytes=0` on observed connection UID `CQN9op1cWFef1nHdCj`.
- Incremental Zeek collector, private SSH receiver and publisher implemented on Linux hosts; retry, deduplication and rotation scenarios validated.
- `systemd` collector and publisher timers activated and automatic runs observed.
- BlueGuard API **v0.4.2-lab** built and deployed to k3s; one Pod ready; endpoints and one Zeek record verified.
- Dashboard polling and UI state updates tested in a separate synthetic preview.

## 2026-11-18 — AWS Traffic Mirroring validation

- LIVE-AD-03/04: controlled 5 MiB HTTP transfers observed at 256 and 64 KiB/s.
- Cross-checked mirror/skip packet counters, network captures and Zeek connection records; quantified missing mirrored packets and Zeek `missed_bytes`.

## 2026-11-16 — Initial application and HTTP capture

- Preserved original BlueGuard API v0.2.0 sources and example Kubernetes deployment.
- Verified a three-request HTTP mirroring smoke test and captured Zeek JSON connection records.
