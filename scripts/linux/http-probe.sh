#!/usr/bin/env bash
# Controlled HTTP only. Run on the Worker only after authorizing the test.
# Does NOT create a mirroring session. Sends no customer data.
set -euo pipefail
for i in 1 2 3; do
  curl -4 --noproxy '*' --silent --show-error --fail \
    --output /dev/null --write-out "Test $i - HTTP %{http_code}\n" \
    --max-time 15 "http://example.com/?blueguard_test=$i"
done
