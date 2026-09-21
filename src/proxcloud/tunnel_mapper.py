from typing import List, Dict, Any
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
            res = self.cf.list_tunnel_routes(t.tunnel_id)
            for r in res.get("result", []):
                # r contains destination and id and other metadata
                routes.append({"tunnel_id": t.tunnel_id, "route": r, "vm_id": t.vm_id})
        return routes

    def ensure_mappings(self):
        # fetch routes and map to expected IPs per mapping
        routes = self.fetch_tunnel_routes()
        for r in routes:
            route = r["route"]
            route_id = route.get("id")
            dest = route.get("destination")
            expected_ip = None
            if dest and dest.startswith("ip:"):
                expected_ip = dest.split("ip:", 1)[1]

            vm_id = r.get("vm_id")
            # discover current IP via proxmox api (or dhcp fallback)
            current_ip = self.api.find_vm_ip(vm_id)
            # persist mapping
            key = f"tunnel:{r['tunnel_id']}:{route_id}"
            self.state.set(key, current_ip or "")
            if expected_ip != current_ip and current_ip:
                # log/update
                print(f"Route {route_id} for tunnel {r['tunnel_id']} expected {expected_ip} but is {current_ip}")
                # update cloudflare
                self.cf.update_tunnel_route(r["tunnel_id"], route_id, f"ip:{current_ip}")
                print(f"Updated route {route_id} -> {current_ip}")
