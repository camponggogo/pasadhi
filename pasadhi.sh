#!/bin/sh
set -eu
cd "$(dirname "$0")"
# Default avoids the 8765 port used by older PASADHI installations.
# Environment override: PASADHI_PORT=8770 ./pasadhi.sh
# Explicit --port in "$@" wins over this default.
if [ -f pasadhi/app/service.py ]; then
    exec python3 -m pasadhi.app.service --host 0.0.0.0 --port "${PASADHI_PORT:-8766}" "$@"
fi
exec python3 app/service.py --host 0.0.0.0 --port "${PASADHI_PORT:-8766}" "$@"
