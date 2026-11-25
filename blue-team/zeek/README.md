# Zeek sensor configuration

This directory contains recovered operational configuration and scripts for the dedicated Zeek 9.0.1 EC2 sensor.

- `etc/node.cfg`: Recovered Zeek node configuration.
- `etc/zeekctl-observed.cfg`: selected effective ZeekCtl settings.
- `site/blueguard-json-logs.zeek`: JSON log configuration.
- `systemd/blueguard-zeek.service`: original Zeek process-management unit, **not** the later collector timer.

The deployed sensor observed AWS VXLAN-encapsulated mirroring on UDP port 4789 and produced Zeek connection records. On 19 November, an **additional** incremental collector was installed and scheduled on the sensor; its installed source and associated `systemd` units were recovered during the 25 November consolidation. See [implementation](../../docs/implementation.md).

Additional recovered components:

- `etc/`: Zeek, ZeekControl and package-manager configuration.
- `site/local.zeek`: recovered site configuration.
- `site/blueguard_exfil/`: data-exfiltration detection policies.
- `libexec/`: incremental collector.
- `sbin/`: healthcheck and watchdog scripts.
- `systemd/`: Zeek, collector, maintenance and watchdog units.
- `FILE-METADATA.txt`: original Linux permissions and ownership.
- `SENSOR-PROVENANCE.txt`: recovery-time environment inventory.

**Read-only checks on sensor:**

```bash
sudo /opt/zeek/bin/zeekctl status
systemctl is-active blueguard-zeek-collector.timer
sudo journalctl -u blueguard-zeek-collector.service -n 25 --no-pager
```

Do not overwrite a complete `local.zeek` configuration with the small included fragment or start a second packet listener on UDP/4789. The recovered files do not yet constitute an automated or independently validated Zeek installation. Historical configuration fragments are retained for reference.
