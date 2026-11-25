#!/usr/bin/env bash
set -euo pipefail

UNIT="blueguard-zeek.service"
HEALTHCHECK="/usr/local/sbin/blueguard-zeek-healthcheck.sh"
LOCK="/run/lock/blueguard-zeek-watchdog.lock"
LAST_ATTEMPT="/run/blueguard-zeek-watchdog.last"
COOLDOWN=600

# Prevent overlapping executions.
exec 9>"$LOCK"

if ! flock -n 9; then
    echo "SKIPPED: another watchdog execution is running"
    exit 0
fi

# Never recover a deliberately stopped service.
if ! systemctl is-active --quiet "$UNIT"; then
    echo "SKIPPED: Zeek service is inactive"
    exit 0
fi

# Healthy sensor: nothing to do.
if "$HEALTHCHECK"; then
    echo "WATCHDOG: no recovery required"
    exit 0
fi

echo "WARNING: Zeek health check failed" >&2

now="$(date +%s)"
previous=0

if [[ -f "$LAST_ATTEMPT" ]]; then
    previous="$(cat "$LAST_ATTEMPT")"
fi

# Prevent repeated restart attempts.
if [[ "$previous" =~ ^[0-9]+$ ]] &&
   (( now >= previous && now - previous < COOLDOWN )); then
    echo "WARNING: recovery cooldown active" >&2
    exit 1
fi

# Check again before changing service state.
if ! systemctl is-active --quiet "$UNIT"; then
    echo "SKIPPED: service was stopped during the check"
    exit 0
fi

# Record the attempt before restarting.
printf '%s\n' "$now" > "$LAST_ATTEMPT"

echo "RECOVERY: restarting $UNIT"

if ! systemctl restart "$UNIT"; then
    echo "ERROR: systemd restart failed" >&2
    exit 1
fi

# Allow Zeek to initialize the socket.
for attempt in 1 2 3 4 5; do
    if systemctl is-active --quiet "$UNIT" && "$HEALTHCHECK"; then
        echo "RECOVERED: Zeek is operational"
        exit 0
    fi

    sleep 2
done

echo "ERROR: Zeek remains unhealthy after restart" >&2
exit 1
