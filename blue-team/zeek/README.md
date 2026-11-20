# Zeek sensor configuration

This directory preserves observed configuration fragments and an early `systemd` service unit for the dedicated Zeek EC2 sensor.

- `etc/node.cfg`: Zeek node configuration fragment.
- `etc/zeekctl-observed.cfg`: selected effective ZeekCtl settings.
- `site/blueguard-json-logs.zeek`: JSON log configuration.
- `systemd/blueguard-zeek.service`: original Zeek process-management unit, **not** the later collector timer.

The deployed sensor observed AWS VXLAN-encapsulated mirroring on UDP port 4789 and produced Zeek connection records. On 19 November, an **additional** incremental collector was installed and scheduled on the sensor; its v0.4.2 source and `systemd` unit files were **not included** in this archive. See [implementation](../../docs/implementation.md).

**Read-only checks on sensor:**

```bash
sudo /opt/zeek/bin/zeekctl status
systemctl is-active blueguard-zeek-collector.timer
sudo journalctl -u blueguard-zeek-collector.service -n 25 --no-pager
```

Do not overwrite a complete `local.zeek` configuration with the small included fragment or start a second packet listener on UDP/4789. The files are selected historical examples rather than a full reproducible Zeek installation.
