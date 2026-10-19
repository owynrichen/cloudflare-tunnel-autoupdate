#!/usr/bin/env python3
"""Top-level runner to check tunnels and optionally apply updates.

Usage: check_tunnels.py <mappings.yaml> [--apply] [--node NODE]
"""
import argparse
import yaml
from proxcloud.tunnel_mapper import TunnelMapper
from proxcloud.config import load_config


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mappings")
    p.add_argument("--apply", action="store_true", help="Apply changes instead of dry-run")
    p.add_argument("--node", default="pve", help="Proxmox node name to use for MAC scanning")
    args = p.parse_args()

    tm = TunnelMapper(args.mappings)

    # run mac scan to build mac->ip map (call scanner programmatically)
    from scripts.scan_macs import scan_node

    out, mac_map = scan_node(args.node)
    print("Scan results:")
    print(out)

    planned = tm.ensure_mappings(dry_run=not args.apply, mac_ip_map=mac_map)
    print("Planned changes:")
    print(yaml.safe_dump(planned))


if __name__ == "__main__":
    main()
