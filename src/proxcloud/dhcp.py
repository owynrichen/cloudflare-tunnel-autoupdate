import glob
import re
from typing import Optional, List


def _parse_isc_leases(content: str):
    # crude parser for isc-dhcpd lease file blocks
    # match 'lease <ip> { ... hardware ethernet <mac>; ... client-hostname "name"; ... }'
    leases = {}
    # split into blocks on 'lease '
    for m in re.finditer(r"lease\s+(?P<ip>[0-9.]+)\s*\{(?P<body>.*?)\}", content, re.S):
        ip = m.group("ip")
        body = m.group("body")
        mac_m = re.search(r"hardware ethernet\s+(?P<mac>[0-9a-f:]+);", body, re.I)
        name_m = re.search(r"client-hostname\s+\"(?P<name>[^\"]+)\";", body)
        mac = mac_m.group("mac") if mac_m else None
        name = name_m.group("name") if name_m else None
        leases[ip] = {"mac": mac, "name": name}
    return leases


def _parse_dnsmasq_leases(content: str):
    # dnsmasq: each line: <expiry> <mac> <ip> <hostname> <client-id>
    leases = {}
    for line in content.splitlines():
        parts = line.split()
        if len(parts) >= 4:
            mac = parts[1]
            ip = parts[2]
            name = parts[3]
            leases[ip] = {"mac": mac, "name": name}
    return leases


def find_ip_for(vm_identifier: str, lease_paths: Optional[List[str]] = None) -> Optional[str]:
    """Search dhcp lease files for a vm identifier (MAC or hostname). Return IP or None.

    If lease_paths is provided, scan those files (or glob patterns). Otherwise use common defaults.
    """
    if lease_paths is None:
        paths = glob.glob("/var/lib/dhcp/*.leases") + glob.glob("/var/lib/dnsmasq/*.leases")
    else:
        paths = []
        for p in lease_paths:
            paths.extend(glob.glob(p))

    for p in paths:
        try:
            with open(p, "r") as f:
                content = f.read()
        except Exception:
            continue
        if "dhcpd" in p or "dhcp" in p:
            leases = _parse_isc_leases(content)
        else:
            leases = _parse_dnsmasq_leases(content)
        for ip, info in leases.items():
            if info.get("mac") and vm_identifier.lower() == info.get("mac").lower():
                return ip
            if info.get("name") and vm_identifier == info.get("name"):
                return ip
    return None
