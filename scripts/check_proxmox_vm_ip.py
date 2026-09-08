#!/usr/bin/env python3
"""Check a VM's IP via the Proxmox API using the project's ProxmoxAPI class.

Usage:
  # export env vars (recommended, avoids putting token on the command line)
  export PROXMOX_API_URL="https://proxmox.example"
  export PROXMOX_API_TOKEN="token@pam!mytoken"
  uv run -- python scripts/check_proxmox_vm_ip.py --vmid 100

Or pass arguments directly (less secure since command line may be stored in history):
  uv run -- python scripts/check_proxmox_vm_ip.py --base-url https://... --token "token@pam!xxx" --vmid 100
"""
from __future__ import annotations
import argparse
import os
import sys
from proxcloud.proxmox_api import ProxmoxAPI


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Check Proxmox VM IP via API")
    p.add_argument("--base-url", help="Proxmox base URL (can be set via PROXMOX_API_URL)")
    p.add_argument("--token", help="Proxmox API token (can be set via PROXMOX_API_TOKEN)")
    p.add_argument("--vmid", required=True, help="VM ID to query")
    args = p.parse_args(argv)

    base = args.base_url or os.environ.get("PROXMOX_API_URL")
    token = args.token or os.environ.get("PROXMOX_API_TOKEN")
    vmid = args.vmid

    if not base or not token:
        print("ERROR: base URL and token must be supplied either via flags or PROXMOX_API_URL/PROXMOX_API_TOKEN env vars", file=sys.stderr)
        return 2

    api = ProxmoxAPI(base, token)
    try:
        ip = api.find_vm_ip(vmid)
    except Exception as e:
        print(f"ERROR: exception while fetching VM IP: {e}")
        return 1

    if ip:
        print(f"VM {vmid} -> IP: {ip}")
        return 0
    else:
        print(f"VM {vmid} -> IP: NOT FOUND")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
