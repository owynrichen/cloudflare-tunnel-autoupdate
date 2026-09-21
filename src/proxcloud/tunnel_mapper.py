from typing import List, Dict, Any
import yaml

from .cloudflare_client import CloudflareClient
from .mapping import load_mappings
from .proxmox_api import ProxmoxAPI
from .state import State
from .config import load_config


class TunnelMapper:
    def __init__(self, mappings_path: str, state_db: str | None = None):
        cfg = load_config()
        self.cf = CloudflareClient(cfg.cloudflare_token, cfg.cloudflare_account)
        self.mappings = load_mappings(mappings_path)
        self.api = ProxmoxAPI(cfg.proxmox_api_url, cfg.proxmox_api_token)
        self.state = State(state_db or cfg.state_db)

    def fetch_tunnel_routes(self) -> List[Dict[str, Any]]:
        routes = []
        for t in self.mappings.tunnels:
            try:
                res = self.cf.list_tunnel_routes(t.tunnel_id)
            except Exception as e:
                # skip tunnels we cannot query (missing id/permissions) but continue processing others
                print(f"warning: failed to list routes for tunnel {t.tunnel_id}: {e}")
                continue
            for r in res.get("result", []):
                # r contains destination and id and other metadata
                routes.append({"tunnel_id": t.tunnel_id, "route": r, "vm_id": t.vm_id})
        return routes

    def export_mappings_from_cloudflare(self) -> Dict[str, Any]:
        """Build a mappings-like dict from Cloudflare tunnels/routes.

        The resulting structure mirrors examples/mappings.example.yaml but does
        not attempt to assign vm_ids. The consumer can manually edit vm_id values
        afterwards to tie routes to VMs.
        """
        out = {"tunnels": []}
        # fetch list of tunnels on account
        try:
            tunnels = self.cf.list_tunnels().get("result", [])
        except Exception as e:
            print(f"warning: failed to list tunnels: {e}")
            tunnels = []

        for t in tunnels:
            tid = t.get("id")
            # fetch routes for tunnel
            try:
                routes = self.cf.list_tunnel_routes(tid).get("result", [])
            except Exception as e:
                print(f"warning: failed to list routes for tunnel {tid}: {e}")
                routes = []
            for r in routes:
                out["tunnels"].append({
                    "tunnel_id": tid,
                    "route_id": r.get("id"),
                    "destination": r.get("destination"),
                    "vm_id": None,
                })
        return out

    def ensure_mappings(self, dry_run: bool = True) -> List[Dict[str, Any]]:
        """Ensure tunnel routes point to current VM IPs.

        If dry_run is True (default) no Cloudflare or state updates are performed;
        the function returns a list of planned changes. If dry_run is False the
        changes are applied and persisted to state.
        """
        planned_changes: List[Dict[str, Any]] = []
        routes = self.fetch_tunnel_routes()
        for r in routes:
            route = r["route"]
            route_id = route.get("id")
            dest = route.get("destination")
            expected_ip = None
            if dest and isinstance(dest, str) and dest.startswith("ip:"):
                expected_ip = dest.split("ip:", 1)[1]

            vm_id = r.get("vm_id")
            current_ip = None
            if vm_id:
                current_ip = self.api.find_vm_ip(vm_id)
            # record planned action if mismatch
            entry = {
                "tunnel_id": r["tunnel_id"],
                "route_id": route_id,
                "expected_ip": expected_ip,
                "current_ip": current_ip,
                "will_update": False,
            }
            if current_ip and expected_ip != current_ip:
                entry["will_update"] = True
                planned_changes.append(entry)
                if not dry_run:
                    # apply update
                    try:
                        self.cf.update_tunnel_route(r["tunnel_id"], route_id, f"ip:{current_ip}")
                        self.state.set(f"tunnel:{r['tunnel_id']}:{route_id}", current_ip)
                        print(f"Updated route {route_id} -> {current_ip}")
                    except Exception as e:
                        print(f"error updating route {route_id}: {e}")
        return planned_changes
