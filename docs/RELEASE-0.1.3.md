# PASADHI v0.1.3

Adds /dashboard and node/cluster resource APIs with explicit reporting coverage,
offline states and deduplication. Adds terminal links to every supported read-only
page/API, using the actual bound port, local/LAN interfaces and optional configured
DNS URL. Adds .env.example and LAN/DNS setup instructions. Keeps first-run earnings
persistence fixes and the seven-language settings page.

All five platforms are rebuilt from the matching source tree. Windows contains a
new native EXE. Linux/macOS require Python 3.10+ and psutil; Android uses Termux.
See COORDINATOR.md for units, topology, setup and validation limits.
