#!/usr/bin/env bash
# Read-only checks. Run on the Zeek EC2, not on Kubernetes nodes.
set -u
failed=0
printf '\n== systemd ==\n'
systemctl is-enabled blueguard-zeek.service || failed=1
systemctl is-active blueguard-zeek.service || failed=1
printf '\n== ZeekControl ==\n'
sudo -u zeek /opt/zeek/bin/zeekctl status || failed=1
printf '\n== UDP listener ==\n'
sudo ss -lunp 'sport = :4789' || failed=1
printf '\n== Owner of mutable state ==\n'
sudo stat -c '%U:%G %a %n' /opt/zeek/spool/state.db || failed=1
printf '\n== Storage ==\n'
df -h /opt/zeek
printf '\nInspect output: active(exited) and a successful status command alone do not prove packet ingestion.\n'
exit "$failed"
