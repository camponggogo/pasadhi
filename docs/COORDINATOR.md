# Coordinator dashboard v0.1.3

After starting the Linux shell launcher, open http://127.0.0.1:8766/dashboard.
Windows/macOS default to http://127.0.0.1:8765/dashboard.
Linux overrides: `PASADHI_PORT=8770 ./pasadhi.sh` or `./pasadhi.sh --port 8770`.
The shell default is a CLI argument, so a port in .env alone does not override it.
The terminal prints all supported page/API URLs and the actual bound port.
The homepage also links to the dashboard. A coordinator label alone does not
connect machines: worker addresses must be configured explicitly.

## Example trusted LAN

The following example uses port 8765. On Linux, start with
`./pasadhi.sh --port 8765` to match it, or change all worker/public URLs to 8766.

On each worker, copy .env.example to .env in the folder containing pasadhi.sh,
PASADHI.command or PASADHI.bat. Set PASADHI_HOST=0.0.0.0. Allow the chosen
port through the local firewall only for the intended LAN. Restart PASADHI.

On the coordinator:

```dotenv
PASADHI_HOST=0.0.0.0
PASADHI_PORT=8765
PASADHI_WORKERS=http://worker-1.lan:8765,http://worker-2.lan:8765
PASADHI_PUBLIC_URL=http://pasadhi-coordinator.lan:8765
```

Then open http://pasadhi-coordinator.lan:8765/dashboard from the LAN.
Use your actual names or IP addresses. Reserve device addresses through router
DHCP and configure router/DNS host records for stable names. PASADHI_PUBLIC_URL
only supplies the displayed URL; it does not create DNS records. If the DNS
record's IP changes, connections resolve the name again, subject to DNS caches.
`.local` requires working mDNS (for example Avahi/Bonjour); support varies by OS.
No automatic mDNS advertisement or automatic node discovery is implemented.

## Reading the numbers

- Total: sum of capacity from currently reporting unique node IDs.
- Shared: configured contribution limits, not a reservation or currently free pool.
- Used: measured host CPU, memory and disk activity, including other apps.
- CPU is summed as busy core equivalents, not an unweighted average of percentages.
- RAM uses total minus available memory. Disk covers the home-directory volume.
- PASADHI RSS is its service process's memory; network counters cover all host apps
  since boot and are not live network throughput or charged traffic.
- GPU capacity comes from hardware probing; GPU usage is unavailable in this release.
- Offline and stale (>30 s, including clock skew) reports are excluded from totals.
- Missing measurements stay unavailable with reporting coverage; never zero-filled.
- Duplicate IDs are counted once. Configure one service per physical machine to
  avoid double-counting hardware through distinct identities on the same host.

The browser refreshes every 15 seconds. Remote collection uses at most 16 concurrent
connections, 1.5-second request timeouts and a maximum of 128 configured endpoints.
An unreachable endpoint stays visible as offline. Every worker needs v0.1.3 telemetry.

This is resource monitoring, not distributed job scheduling or job-level resource
accounting. Default binding is loopback. On LAN, these read-only endpoints follow
the app's existing access model; use a trusted network or an authenticated reverse
proxy rather than exposing this service directly to the Internet.

## Verification

Unit/HTTP tests cover aggregation, offline and duplicate nodes, missing GPU usage,
stale/invalid payloads, configured URL validation, startup links and macOS paths.
Integration uses three isolated processes on one Windows host, not three physical
machines. The Windows EXE is tested from its release ZIP. Linux packages are tested
through WSL; native macOS/Android execution is still unverified.
