#!/usr/bin/env bash
set -euo pipefail

UNIT="blueguard-zeek.service"
ZEEKCTL="/opt/zeek/bin/zeekctl"

# Respect an intentional stop through systemd.
if ! systemctl is-active --quiet "$UNIT"; then
    echo "SKIPPED: BlueGuard Zeek service is inactive"
    exit 0
fi

# Retrieve the PID reported by ZeekControl.
status="$(runuser -u zeek -- "$ZEEKCTL" status)"

pid="$(
    printf '%s\n' "$status" |
    awk '$1=="zeek" && $4=="running" && $5~/^[0-9]+$/ {
        print $5
        exit
    }'
)"

if [[ -z "$pid" ]]; then
    echo "UNHEALTHY: ZeekControl does not report a running process" >&2
    exit 1
fi

# Verify the actual process identity.
owner="$(ps -o user= -p "$pid" 2>/dev/null || true)"
name="$(ps -o comm= -p "$pid" 2>/dev/null || true)"

owner="${owner//[[:space:]]/}"
name="${name//[[:space:]]/}"

if [[ "$owner" != "zeek" || "$name" != "zeek" ]]; then
    echo "UNHEALTHY: Unexpected process identity for PID $pid" >&2
    exit 1
fi

# Verify that the process owns the VXLAN UDP socket.
if ! ss -H -lunp | awk -v pid="$pid" '
    $4=="0.0.0.0:4789" &&
    index($0, "pid=" pid ",") {
        found=1
    }
    END { exit !found }
'; then
    echo "UNHEALTHY: Zeek is not listening on UDP 4789" >&2
    exit 1
fi

echo "HEALTHY: Zeek PID $pid, user zeek, UDP 4789 listening"
