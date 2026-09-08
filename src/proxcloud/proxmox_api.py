import requests
from typing import Optional
from .config import load_config


class ProxmoxAPI:
    def __init__(self, base_url: str, token: str):
        # normalize base URL: remove any trailing '/api2/json' if present to
        # avoid duplicating the api path when building endpoints.
        b = base_url.rstrip("/")
        if b.endswith("/api2/json"):
            b = b[: -len("/api2/json")]
        self.base = b
        self.token = token
        self.headers = {"Authorization": f"PVEAPIToken={self.token}"}

    def get_vm_interfaces(self, node: str, vmid: str) -> Optional[dict]:
        # Attempt to read guest network info via QEMU agent info endpoint
        url = f"{self.base}/api2/json/nodes/{node}/qemu/{vmid}/agent/network-get-interfaces"
        r = requests.get(url, headers=self.headers, timeout=5)
        r.raise_for_status()
        return r.json().get("data")

    def find_vm_ip(self, vmid: str) -> Optional[str]:
        # naive: iterate nodes and qemu VMs to find matching vmid. In real usage you may need
        # to supply node or full vmid (like vm@node). Here we assume vmid is the numeric id and
        # that nodes are discoverable.
        url = f"{self.base}/api2/json/cluster/resources?type=vm"
        r = requests.get(url, headers=self.headers, timeout=5)
        r.raise_for_status()
        for item in r.json().get("data", []):
            if str(item.get("vmid")) == str(vmid):
                node = item.get("node")
                data = self.get_vm_interfaces(node, vmid)
                # data may be a dict mapping interface names to info, or a list
                # of interface objects depending on the Proxmox/config/version.
                # Normalize into an iterable of interface info dicts.
                interfaces = []
                if not data:
                    interfaces = []
                elif isinstance(data, dict):
                    # entries may be { ifname: {...} }
                    # or { 'result': {...} } depending on agent response
                    # accept either shape
                    # If values are dicts with 'ip-addresses', use them
                    for v in data.values():
                        if isinstance(v, dict):
                            interfaces.append(v)
                elif isinstance(data, list):
                    interfaces = data

                # iterate and pick first usable IPv4, fallback to IPv6 if needed
                ipv6_fallback = None
                for info in interfaces:
                    addrs = info.get("ip-addresses") or info.get("ip_addresses") or []
                    for a in addrs:
                        fam = a.get("family")
                        ip = a.get("ip-address") or a.get("ip_address")
                        if not ip:
                            continue
                        # strip CIDR suffix if present
                        if "/" in ip:
                            ip = ip.split("/")[0]
                        if fam == "ipv4":
                            return ip
                        if fam == "ipv6" and ipv6_fallback is None:
                            ipv6_fallback = ip
                if ipv6_fallback:
                    return ipv6_fallback
        return None
