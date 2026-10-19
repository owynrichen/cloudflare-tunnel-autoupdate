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
    p.add_argument("--probe", action="store_true", help="Probe VMs to detect http/https when destination is missing")
    p.add_argument("--insecure-tls", action="store_true", help="Allow insecure TLS when probing HTTPS")
    p.add_argument("--auto-assign", action="store_true", help="Auto-assign vm_id values in mappings using heuristics")
    p.add_argument("--out", default="examples/mappings.generated.yaml", help="Output path for generated mappings when auto-assigning")
    args = p.parse_args()

    tm = TunnelMapper(args.mappings)

    # run mac scan to build mac->ip map (call scanner programmatically)
    # import scanner module — support running as script from repo root or as module
    try:
        from scripts.scan_macs import scan_node
    except ModuleNotFoundError:
        from scan_macs import scan_node

    out, mac_map = scan_node(args.node)
    print("Scan results:")
    print(out)

    # If requested, export mappings and attempt to auto-assign vm_ids
    if args.auto_assign:
        try:
            exported = tm.export_mappings_from_cloudflare()
            # auto-assign uses vm scan results to find candidates
            exported = tm.auto_assign_vm_ids(exported, out, mac_map)
            with open(args.out, "w") as fh:
                import yaml

                yaml.safe_dump(exported, fh)
            print(f"Wrote auto-assigned mappings to {args.out}")
            # reload mappings from output for subsequent operations
            tm = TunnelMapper(args.out)
        except Exception as e:
            print(f"warning: auto-assign failed: {e}")

    planned = tm.ensure_mappings(dry_run=not args.apply, mac_ip_map=mac_map, probe=args.probe, allow_insecure_tls=args.insecure_tls)
    print("Planned changes:")
    print(yaml.safe_dump(planned))


if __name__ == "__main__":
    main()
