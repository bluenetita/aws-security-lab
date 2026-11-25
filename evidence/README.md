# Evidence and data provenance

This directory contains **selected structured transcriptions** of terminal results and a small number of retained example records. It is not a complete collection of PCAP files, original CloudWatch exports, Zeek archives, service journals or application source.

- [`2026-11-16/`](2026-11-16/): initial HTTP request/response observations.
- [`2026-11-18/result.json`](2026-11-18/result.json): LIVE-AD-03 and LIVE-AD-04 metrics and historical shutdown observations.
- [`2026-11-19/result.json`](2026-11-19/result.json): LIVE-AD-05, ingestion, timers, API deployment and synthetic-preview checks.
- [`2026-11-24/result.json`](2026-11-24/result.json): selected TCP/UDP diagnostic observations, rc4 QA, image checks, Canary/promotion and final Service telemetry. No new AWS shutdown or raw packet capture is asserted.
- [`operations/shutdown-check.json`](operations/shutdown-check.json): later AWS CLI report of four stopped EC2 instances and zero Traffic Mirroring sessions; exact UTC capture time not available.

These records are **reported observations**, not independent live verification. Controlled test payloads and private IP addresses may appear; review policies before publication.
