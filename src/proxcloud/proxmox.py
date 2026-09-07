import subprocess
from typing import Dict, Optional


from typing import Optional, List
from .dhcp import find_ip_for
from .config import load_config
from .proxmox_api import ProxmoxAPI


def get_guest_ip(vm_id: str, lease_paths: Optional[List[str]] = None) -> Optional[str]:
    """Resolve a guest IP. Prefer Proxmox API if configured, otherwise use DHCP lease files.

    lease_paths: optional list of lease file paths or glob patterns to scan.
    """
    cfg = load_config()
    if cfg.proxmox_api_url and cfg.proxmox_api_token:
        api = ProxmoxAPI(cfg.proxmox_api_url, cfg.proxmox_api_token)
        ip = api.find_vm_ip(vm_id)
        if ip:
            return ip
    # fallback to lease scanning
    return find_ip_for(vm_id, lease_paths)
