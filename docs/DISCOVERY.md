# Automatic discovery of PASADHI computers

Every refreshed PASADHI instance advertises a unique `_pasadhi._tcp.local.` service
and listens for other instances on its selected private LAN IPv4 interfaces.
Worker, client and coordinator roles all participate. Dashboards on any node can
show the other nodes; only one selected coordinator should additionally advertise
the shared `pasadhi.local` hostname through --mdns.

## Start every computer in LAN mode

Windows: double-click PASADHI.bat.
Linux: `python3 -m pip install -r requirements.txt`, then `sh pasadhi.sh`.
macOS: install requirements, then `sh PASADHI.command`.
Termux: install requirements, then `sh pasadhi.sh`.
Source: install requirements, then `sh pasadhi.sh`.

Main launchers bind HTTP to 0.0.0.0 and enable LAN access by default. Install
requirements.txt before starting Python bundles. For localhost-only access, pass
`--host 127.0.0.1` to the launcher; that node appears as `lan-disabled` elsewhere.
The direct Python/EXE command still accepts `--lan`. No firewall rule is changed.
Legacy LAN-named launchers remain compatibility aliases; they are not required.

All computers need this refreshed build. The version remains 0.1.3 at the owner's
request, so compare the current release manifest/checksum or download again.
The prior 0.1.3 archives and the earlier mDNS-source-only change did not discover peers.

## What happens

The service's TXT metadata identifies its node ID, role, resource schema and LAN
availability. Discovery is inventory, not proof of identity or trust. Advertised
addresses are accepted only within local private IPv4 interface subnets; loopback,
link-local metadata endpoints, public IPs and off-subnet addresses are not queried
by production discovery. A hard limit bounds retained service entries and fetch
concurrency. No credentials are broadcast. Use this on a trusted LAN.

The dashboard polls the node resource API, checks schema, freshness and node ID,
and aggregates reachable nodes. Duplicate identities are counted once. A normal
service goodbye removes a peer; lost devices eventually expire from the DNS-SD
cache. While a peer remains known but HTTP fails it is shown offline. IP changes
recreate multicast interfaces and update announcements, subject to client caches.

Use PASADHI_MDNS_INTERFACE to select a physical NIC if automatic interface
selection chooses the wrong LAN. Common virtual/VPN adapter prefixes are excluded
by default. PASADHI_DISCOVERY=0 or --no-discovery disables peer announcements and
browsing. PASADHI_WORKERS remains an explicit fallback for routed/VLAN networks.

## If only this machine appears

1. Use the refreshed main launcher on every node and install Python requirements where needed.
2. Check the dashboard's discovery status. A dependency or interface error is shown.
3. Keep the computers on the same multicast-capable LAN. Guest/client isolation,
   VPNs and VLANs can prevent service discovery even with similar Wi-Fi names.
4. Allow UDP 5353 multicast and the app's displayed TCP port on the intended LAN.
5. Test the other computer's displayed LAN dashboard URL directly. If it fails,
   check binding/firewall first. Manual PASADHI_WORKERS URLs can bypass missing
   multicast, but cannot bypass a blocked TCP connection.

Tests cover service events, IP changes, same-LAN filtering, localhost-only nodes,
identity mismatches, automatic aggregation without configured IPs, and goodbye
removal. A real multicast/HTTP loopback test does not certify a particular router,
firewall, or physical multi-machine deployment.

## Shared dashboard snapshot

Cards show measured used / total capacity. Every updated node elects the same
snapshot source: coordinator roles first, then the smallest node ID. The selected
source caches one immutable cluster snapshot per 15-second epoch; other nodes
fetch that snapshot instead of independently measuring totals. Snapshot ID and
sample time are displayed. Browser refresh aligns to the same epoch. During
discovery convergence or different network partitions, node membership may differ;
identical views require the same discovered peers and reachable, updated source.
Unavailable sources show a visible degraded local view, never a false sync claim.
All nodes must download this refreshed build. GPU unavailable remains unavailable.
