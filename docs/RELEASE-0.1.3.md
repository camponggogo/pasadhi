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

## Refreshed LAN discovery packages

Adds automatic DNS-SD discovery for all roles, visible LAN-disabled states, LAN
launchers and per-node dashboard links. Includes coordinator hostname mDNS and its
required dependencies in the rebuilt Windows EXE. Python bundles require their
updated requirements.txt. Version stays 0.1.3; archives/checksums are refreshed.

## LAN defaults, 5 November 2026

All main platform launchers now bind to 0.0.0.0 by default. Use PASADHI.bat,
pasadhi.sh or PASADHI.command; separate LAN launchers are compatibility aliases.
Pass --host 127.0.0.1 for localhost-only access. Python bundles still require
requirements.txt (including zeroconf). No firewall settings change. Version remains
0.1.3; re-download all packages and compare refreshed checksums.

## Shared dashboard resource snapshot, 5 November 2026

Cards show used / total. Dashboards elect one coordinator snapshot source and
share cached 15-second samples, with snapshot ID and degraded-state visibility.
All nodes need refreshed packages. Version remains 0.1.3.
