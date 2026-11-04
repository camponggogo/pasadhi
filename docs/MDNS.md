# Stable coordinator name on a LAN

Refreshed 0.1.3 packages include opt-in coordinator hostname advertisement and
automatic peer discovery. Replace older downloads on every node. The app
never edits router DNS, firewall rules, hosts files or system proxy configuration.

## Direct URL with the actual application port

From the updated repository, install its requirements and start one coordinator:

```sh
python3 -m pip install -r requirements.txt
sh pasadhi.sh --role coordinator --host 0.0.0.0 --mdns
```

The Linux launcher uses 8766 by default, so the announced dashboard URL is:

http://pasadhi.local:8766/dashboard

For another port, append --port 8770. A source run on Windows can use:

```powershell
python app/service.py --role coordinator --host 0.0.0.0 --port 8766 --mdns
```

Only a coordinator explicitly bound to all IPv4 interfaces can enable this option.
Workers and the default loopback-only service do not publish a hostname. The app
polls interface addresses every five seconds. When addresses change it withdraws
its old service, recreates multicast sockets and announces the new IPv4 addresses
under the same name. Announced records have a 60-second TTL. Shutdown withdraws
its service. Client caches and network loss can delay resolution after an IP change.

Set PASADHI_MDNS_INTERFACE to a NIC name to select one adapter (e.g. eth0 or Wi-Fi 2).
Without a selection, active private IPv4 interfaces are used; common virtual/VPN
adapter prefixes are excluded. No usable address means the app waits and retries.
IP-based URLs remain available if registration fails. Errors are logged; a known
competing service is not silently renamed. Reserve pasadhi.local for one coordinator
and do not assign that hostname to another device. mDNS does not provide identity
authentication or protection against another device claiming the name.

## Exact URL without a port

http://pasadhi.local/dashboard uses HTTP port 80, so a proxy must actually listen on
80 and forward to the application's port. mDNS alone cannot make browsers use an
SRV-advertised nondefault port for an ordinary URL.

The optional deploy/Caddyfile.pasadhi-local forwards HTTP on pasadhi.local to
127.0.0.1:8766. Install Caddy separately using its official instructions, verify port
80 is available, and have the OS service manager run Caddy with permission to bind
80. Do not run PASADHI itself as root just to obtain a short URL. Validate and run
that configuration using your normal Caddy service workflow. It is an example,
not an automatically installed or enabled proxy.

Once the proxy is configured, launch the coordinator with:

```sh
sh pasadhi.sh --role coordinator --host 0.0.0.0 --mdns --mdns-port 80
```

The advertised service port is now 80 and the printed mDNS URL omits the port.
PASADHI does not verify or start the proxy; check its HTTP response independently.
PASADHI_PUBLIC_URL=http://pasadhi.local can also list this configured URL at startup.
It is a display setting and still does not create DNS records.

## Environment configuration

The same source options can be set in .env or the process environment:

```dotenv
PASADHI_HOST=0.0.0.0
PASADHI_MDNS=1
PASADHI_MDNS_NAME=pasadhi
PASADHI_MDNS_INTERFACE=
PASADHI_MDNS_PORT=
```

Continue to pass --role coordinator. Set PASADHI_MDNS_PORT=80 only with a working
proxy. Use a different valid label with --mdns-name for a deliberately separate
coordinator; the name is never changed automatically on conflict.

## Client and network support

The client OS/browser must resolve .local using mDNS. Linux may need Avahi/nss-mdns,
Windows support varies by resolver/application, and Android behavior varies by
version. Clients must be in a multicast-capable LAN; Wi-Fi client isolation, VPNs,
firewalls and separate VLANs can block UDP 5353. No rule is changed automatically.
A multicast test with two Zeroconf endpoints does not certify browser resolution
on every OS. Use the printed IP URL when the client cannot resolve .local.

Unit tests cover address changes, disconnect/reconnect, conflicts and cleanup.
An independent real Zeroconf receiver also resolved a unique test service's A/SRV
records over loopback. No production LAN pasadhi.local record or port-80 proxy was
installed on the developer's machine as part of testing.

References: [python-zeroconf API](https://python-zeroconf.readthedocs.io/en/stable/api.html),
[Caddy reverse_proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy),
[Caddy automatic HTTPS and explicit HTTP](https://caddyserver.com/docs/automatic-https).
