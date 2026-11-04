# PASADHI v0.1.3

Adds /dashboard and node/cluster resource APIs with explicit reporting coverage,
offline states and deduplication. Adds terminal links to every supported read-only
page/API, using the actual bound port, local/LAN interfaces and optional configured
DNS URL. Adds .env.example and LAN/DNS setup instructions. Keeps first-run earnings
persistence fixes and the seven-language settings page.

All five platforms are rebuilt from the matching source tree. Windows contains a
new native EXE. Linux/macOS require Python 3.10+ and psutil; Android uses Termux.
See COORDINATOR.md for units, topology, setup and validation limits.

## Same-version launcher update 4 November 2026

At the owner's request, filenames and version remain 0.1.3. Linux pasadhi.sh now
passes --port 8766 by default (PASADHI_PORT environment or an explicit --port can
override it). Port conflicts now show an actionable message. The listener binds
before a worker starts. Shutdown and --once close the listener. Source bundles and
Windows EXE include the startup fix. SHA256SUMS and manifests identify refreshed
archives; re-download the package to receive this update.
