#!/bin/sh
set -eu
# Runtime UID may be the host user's UID when an existing library is mounted.
# Give provider CLIs a private, writable home without changing host permissions.
HOME="$(mktemp -d /tmp/researchos-home-XXXXXX)"
export HOME
umask 077
exec "$@"
