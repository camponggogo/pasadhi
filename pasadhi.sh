#!/bin/sh
set -eu
cd "$(dirname "$0")"
# Default avoids the 8765 port used by older PASADHI installations.
# Environment override: PASADHI_PORT=8770 ./pasadhi.sh
# Explicit --port in "$@" wins over this default.
exec python3 -m pasadhi.app.service --port "${PASADHI_PORT:-8766}" "$@"
