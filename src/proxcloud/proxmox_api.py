import logging
import time
from typing import Optional

import requests
from requests import exceptions as req_exceptions

from .config import load_config
from .dhcp import find_ip_for
import re

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
        # token may be either the full header value or just the token secret.
        # If a separate token id is present in env/config, combine them.
        self.token = token
        try:
            cfg = load_config()
            tid = getattr(cfg, "proxmox_api_token_id", None)
        except Exception:
            tid = None

        if tid and self.token:
            header_val = f"PVEAPIToken={tid}={self.token}"
        elif self.token and self.token.startswith("PVEAPIToken="):
            header_val = self.token
        elif self.token:
            # token provided but no id: use as-is (best-effort)
            header_val = f"PVEAPIToken={self.token}"
        else:
            header_val = ""

        self.headers = {"Authorization": header_val} if header_val else {}
        # honor verify setting from project config if present
        try:
            cfg = load_config()
            self.verify = cfg.proxmox_api_verify
        except Exception:
            # if config not loadable during tests, default to True
            self.verify = True

    def _get(self, url: str) -> Optional[requests.Response]:
        """Perform a GET with basic retry/backoff and return Response or None on failure."""
        last_exc = None
        for attempt in range(1, _RETRIES + 1):
            try:
                r = requests.get(url, headers=self.headers, timeout=5, verify=self.verify)
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
            if ip:
                return ip

            # attempt to read vm/container config for MACs or hostname and map via DHCP
            cfg = self.get_vm_config(node, vmid_only)
            ip = self._ip_from_config_or_leases(cfg, vmid_only)
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
                # try config-based MAC -> IP mapping
                cfg = self.get_vm_config(node, vmid_only)
                ip = self._ip_from_config_or_leases(cfg, vmid_only)
                if ip:
                    return ip
        return None

    def get_vm_config(self, node: str, vmid: str) -> Optional[dict]:
        """Fetch VM or container config from the node and return data dict or None."""
        # try qemu config then lxc config
        for url in [
            f"{self.base}/api2/json/nodes/{node}/qemu/{vmid}/config",
            f"{self.base}/api2/json/nodes/{node}/lxc/{vmid}/config",
        ]:
            r = self._get(url)
            if not r:
                continue
            try:
                return r.json().get("data")
            except ValueError:
                continue
        return None

    def _ip_from_config_or_leases(self, cfg: Optional[dict], vmid: str) -> Optional[str]:
        """Given a VM config dict, extract MACs and hostnames and map to IP via DHCP leases."""
        if not cfg:
            return None

        macs = set()
        # config may contain keys like 'net0', 'net1' with values containing MACs
        for k, v in (cfg.items() if isinstance(cfg, dict) else []):
            if k.startswith("net") and isinstance(v, str):
                # search for MAC addresses in the value
                for m in re.findall(r"[0-9a-fA-F:]{17}", v):
                    macs.add(m.lower())
                # lxc may include hwaddr=<mac>
                hw = re.search(r"hwaddr=([0-9a-fA-F:]{17})", v)
                if hw:
                    macs.add(hw.group(1).lower())
        # also try hostname from config
        names = set()
        host = cfg.get("hostname") or cfg.get("name") or cfg.get("hostname")
        if host:
            names.add(host)

        # try DHCP lookup by MACs first
        for m in macs:
            ip = find_ip_for(m)
            if ip:
                return ip

        # fallback: try by hostname/vmid
        for n in list(names) + [vmid]:
            ip = find_ip_for(n)
            if ip:
                return ip

        return None
