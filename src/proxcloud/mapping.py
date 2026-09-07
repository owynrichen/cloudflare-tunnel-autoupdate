from dataclasses import dataclass
from typing import List, Optional
import yaml


@dataclass
class DNSMapping:
    zone: str
    zone_id: Optional[str]
    record_id: Optional[str]
    name: str
    type: str
    vm_id: str
    lease_paths: Optional[List[str]] = None


@dataclass
class TunnelMapping:
    tunnel_id: str
    route_id: str
    vm_id: str
    lease_paths: Optional[List[str]] = None


@dataclass
class ConfigMappings:
    dns: List[DNSMapping]
    tunnels: List[TunnelMapping]


def load_mappings(path: str) -> ConfigMappings:
    with open(path, "r") as f:
        raw = yaml.safe_load(f)
    # global lease paths
    global_leases = raw.get("lease_paths", [])
    dns_list = raw.get("dns", [])
    tunnels_list = raw.get("tunnels", [])

    # inject global lease paths into dns mappings if not present
    dns = []
    for d in dns_list:
        if "lease_paths" not in d and global_leases:
            d["lease_paths"] = global_leases
        dns.append(DNSMapping(**d))

    tunnels = []
    for t in tunnels_list:
        if "lease_paths" not in t and global_leases:
            t["lease_paths"] = global_leases
        tunnels.append(TunnelMapping(**t))

    return ConfigMappings(dns=dns, tunnels=tunnels)
