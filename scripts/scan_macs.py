#!/usr/bin/env python3
"""Scan a given node for VMs/LXCs, extract MACs from config, and map to IPs via ARP/DHCP.

This script is intended to be run locally on a management host with access to the Proxmox API
and the ability to ping the local network to populate ARP tables.
"""
import json
import re
import subprocess
import sys
from proxcloud.config import load_config
from proxcloud.proxmox_api import ProxmoxAPI


def ping_sweep(subnet_prefix: str = "192.168.1"):
    procs = []
    for i in range(1, 255):
        ip = f"{subnet_prefix}.{i}"
        p = subprocess.Popen(["ping", "-c", "1", "-W", "1", ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        procs.append(p)
    for p in procs:
        try:
            p.wait(timeout=2)
        except Exception:
            pass


def read_arp_table():
    out = subprocess.run(["arp", "-an"], capture_output=True, text=True).stdout
    res = {}
    for line in out.splitlines():
        m = re.search(r"\((?P<ip>[^)]+)\) at (?P<mac>[0-9a-f:]{17})", line, re.I)
        if m:
            res[m.group("mac").lower()] = m.group("ip")
    return res


def scan_node(node: str = "pve"):
    cfg = load_config()
    api = ProxmoxAPI(cfg.proxmox_api_url, cfg.proxmox_api_token)

    out = []
    for path in ["qemu", "lxc"]:
        r = api._get(f"{api.base}/api2/json/nodes/{node}/{path}")
        if not r:
            continue
        for entry in r.json().get("data", []):
            vmid = entry.get("vmid")
            name = entry.get("name")
            cfgdata = api.get_vm_config(node, vmid) or {}
            macs = []
            for k, v in cfgdata.items():
                if k.startswith("net") and isinstance(v, str):
                    macs += re.findall(r"[0-9A-Fa-f:]{17}", v)
                    m = re.search(r"hwaddr=([0-9A-Fa-f:]{17})", v)
                    if m:
                        macs.append(m.group(1))
            out.append({"vmid": vmid, "name": name, "macs": [m.lower() for m in macs]})

    # Populate ARP by ping sweep
    ping_sweep()
    arp = read_arp_table()

    # Map MACs to IPs and return structure
    for e in out:
        e["ips"] = [arp.get(m) for m in e["macs"]]

    # Also return a mac->ip map for convenience
    mac_map = {}
    for e in out:
        for m, ip in zip(e["macs"], e["ips"]):
            if ip:
                mac_map[m] = ip

    return out, mac_map


def main_cli():
    node = sys.argv[1] if len(sys.argv) > 1 else "pve"
    out, mac_map = scan_node(node)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main_cli()
