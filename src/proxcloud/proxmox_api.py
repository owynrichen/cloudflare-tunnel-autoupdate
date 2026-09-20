import logging
import time
from typing import Optional

import requests
from requests import exceptions as req_exceptions

from .config import load_config

logger = logging.getLogger(__name__)

# retry behavior for transient network/API errors
_RETRIES = 3
_RETRY_DELAY = 0.1


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

    def _get(self, url: str) -> Optional[requests.Response]:
        """Perform a GET with basic retry/backoff and return Response or None on failure."""
        last_exc = None
        for attempt in range(1, _RETRIES + 1):
            try:
                r = requests.get(url, headers=self.headers, timeout=5)
                r.raise_for_status()
                return r
            except Exception as e:
                # catch all exceptions from requests or from test monkeypatches
                last_exc = e
                logger.debug("request failed (%s) attempt %d/%d: %s", url, attempt, _RETRIES, e)
                if attempt < _RETRIES:
                    time.sleep(_RETRY_DELAY)
        logger.warning("GET %s failed after %d attempts: %s", url, _RETRIES, last_exc)
        return None

    def get_vm_interfaces(self, node: str, vmid: str, vm_type: Optional[str] = None) -> Optional[dict]:
        """Attempt to read guest network info via the QEMU or LXC guest agent.

        vm_type: optionally 'lxc' to force the LXC endpoint. If None, the QEMU
        endpoint is tried first and then LXC as a fallback.
        """
        # choose endpoints
        tried = []
        endpoints = []
        if vm_type == "lxc":
            endpoints = [f"{self.base}/api2/json/nodes/{node}/lxc/{vmid}/agent/network-get-interfaces"]
        elif vm_type == "qemu":
            endpoints = [f"{self.base}/api2/json/nodes/{node}/qemu/{vmid}/agent/network-get-interfaces"]
        else:
            # try qemu first, then lxc
            endpoints = [
                f"{self.base}/api2/json/nodes/{node}/qemu/{vmid}/agent/network-get-interfaces",
                f"{self.base}/api2/json/nodes/{node}/lxc/{vmid}/agent/network-get-interfaces",
            ]

        for url in endpoints:
            tried.append(url)
            r = self._get(url)
            if not r:
                # try next
                continue
            try:
                return r.json().get("data")
            except ValueError:
                logger.warning("invalid json from %s", url)
                return None
        logger.debug("no interfaces found for %s@%s (tried: %s)", vmid, node, tried)
        return None

    def find_vm_ip(self, vmid: str) -> Optional[str]:
        """Find the VM's IP. Accepts vmid or vmid@node. Tries QEMU then LXC guest agent.

        Returns first IPv4 found, otherwise first IPv6. Returns None on errors or no address.
        """
        # if node provided as vmid@node, avoid cluster lookup
        node = None
        vmid_only = vmid
        if "@" in vmid:
            vmid_only, node = vmid.split("@", 1)

        # helper to extract ip from agent data
        def extract_ip(data) -> Optional[str]:
            interfaces = []
            if not data:
                interfaces = []
            elif isinstance(data, dict):
                for v in data.values():
                    if isinstance(v, dict):
                        interfaces.append(v)
            elif isinstance(data, list):
                interfaces = data

            ipv6_fallback = None
            for info in interfaces:
                addrs = info.get("ip-addresses") or info.get("ip_addresses") or []
                for a in addrs:
                    fam = a.get("family")
                    ip = a.get("ip-address") or a.get("ip_address")
                    if not ip:
                        continue
                    if "/" in ip:
                        ip = ip.split("/")[0]
                    if fam == "ipv4":
                        return ip
                    if fam == "ipv6" and ipv6_fallback is None:
                        ipv6_fallback = ip
            return ipv6_fallback

        # if node known, try to query agent directly (qemu then lxc)
        if node:
            data = self.get_vm_interfaces(node, vmid_only)
            try:
                ip = extract_ip(data)
            except Exception:
                ip = None
            if ip:
                return ip
            # try forcing lxc if qemu didn't return anything
            data = self.get_vm_interfaces(node, vmid_only, vm_type="lxc")
            try:
                ip = extract_ip(data)
            except Exception:
                ip = None
            return ip

        # no node: inspect cluster resources for vm or lxc
        url = f"{self.base}/api2/json/cluster/resources"
        r = self._get(url)
        if not r:
            return None
        try:
            items = r.json().get("data", [])
        except ValueError:
            logger.warning("invalid json from cluster resources")
            return None

        for item in items:
            if str(item.get("vmid")) == str(vmid_only):
                node = item.get("node")
                rtype = item.get("type") or item.get("ts") or None
                # map resource type to vm_type param: 'lxc' -> 'lxc', else try qemu
                vm_type = "lxc" if item.get("type") == "lxc" else None
                data = self.get_vm_interfaces(node, vmid_only, vm_type=vm_type)
                try:
                    ip = extract_ip(data)
                except Exception:
                    ip = None
                if ip:
                    return ip
        return None
