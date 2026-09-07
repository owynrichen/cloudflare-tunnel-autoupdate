import requests
from typing import Optional
from .config import load_config


class ProxmoxAPI:
    def __init__(self, base_url: str, token: str):
        self.base = base_url.rstrip("/")
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
                # data is a dict with 'result' per interface; try to find an ip
                for ifname, info in (data or {}).items():
                    addrs = info.get("ip-addresses") or []
                    for a in addrs:
                        if a.get("family") == "ipv4":
                            return a.get("ip-address")
        return None
