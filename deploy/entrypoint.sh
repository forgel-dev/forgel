#!/bin/sh
# The container starts as root only to make the named data volume writable by
# the unprivileged runtime user, then drops privileges. Project code never runs
# as root and the host Docker socket is never used.
set -eu

if [ "$(id -u)" = "0" ]; then
  : "${FORGEL_HOME:=/data}"
  mkdir -p "$FORGEL_HOME"
  if [ "$(stat -c '%u' "$FORGEL_HOME")" != "10001" ]; then
    chown -R 10001:10001 "$FORGEL_HOME"
  fi
  if command -v setpriv >/dev/null 2>&1; then
    exec setpriv --reuid=10001 --regid=10001 --clear-groups "$@"
  fi
  if command -v runuser >/dev/null 2>&1; then
    exec runuser -u forgel -- "$@"
  fi
  echo "forgel: no setpriv or runuser to drop privileges" >&2
  exit 1
fi

exec "$@"
