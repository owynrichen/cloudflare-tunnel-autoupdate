from typing import List, Dict, Any
import yaml
from urllib.parse import urlparse, urlunparse
import requests
from requests.exceptions import RequestException, SSLError, ConnectionError

from .cloudflare_client import CloudflareClient
from .mapping import load_mappings
from .proxmox_api import ProxmoxAPI
from .state import State
from .config import load_config
import re


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

    def auto_assign_vm_ids(self, exported: Dict[str, Any], scan_out: List[Dict[str, Any]], mac_ip_map: Dict[str, str]) -> Dict[str, Any]:
        """Try to assign vm_id for exported mappings using heuristics.

        Heuristics (in order):
        - If destination is ip:<ip> and ip matches a scanned VM IP, assign that vmid
        - If destination hostname matches a VM name, assign that vmid
        - If a VM's MAC-derived IP matches the route destination IP, assign that vmid
        """
        # build helper maps
        ip_to_vmid = {}
        name_to_vmid = {}
        for e in scan_out:
            vmid = str(e.get("vmid"))
            name = e.get("name")
            ips = [i for i in e.get("ips", []) if i]
            for ip in ips:
                ip_to_vmid[ip] = vmid
            if name:
                name_to_vmid[name] = vmid

        for t in exported.get("tunnels", []):
            dest = t.get("destination")
            assigned = None
            if isinstance(dest, str) and dest.startswith("ip:"):
                ip = dest.split("ip:", 1)[1]
                assigned = ip_to_vmid.get(ip)
            if not assigned and isinstance(dest, str):
                # try parse hostname
                try:
                    p = urlparse(dest)
                    hostname = p.hostname
                    if hostname:
                        # direct name match
                        assigned = name_to_vmid.get(hostname)
                except Exception:
                    pass
            # last ditch: check if any scanned VM ip is same as destination host resolved from mac map
            if not assigned and isinstance(dest, str) and dest.startswith("ip:"):
                ip = dest.split("ip:", 1)[1]
                assigned = ip_to_vmid.get(ip)

            t["vm_id"] = assigned

        return exported

    def ensure_mappings(self, dry_run: bool = True, mac_ip_map: Dict[str, str] | None = None, probe: bool = False, allow_insecure_tls: bool = False) -> List[Dict[str, Any]]:
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
            # fallback: try mapping via VM config MACs against provided mac_ip_map
            if not current_ip and mac_ip_map and vm_id:
                cfg = self.api.get_vm_config(self.api.base.split('/nodes/')[0] if False else 'pve', vm_id)
                # above is a no-op to keep signature; fetch actual cfg below
                cfg = self.api.get_vm_config('pve', vm_id)
                if cfg:
                    # collect macs
                    macs = []
                    for k, v in cfg.items():
                        if k.startswith("net") and isinstance(v, str):
                            macs += re.findall(r"[0-9A-Fa-f:]{17}", v)
                            m = re.search(r"hwaddr=([0-9A-Fa-f:]{17})", v)
                            if m:
                                macs.append(m.group(1))
                    for m in macs:
                        ip = mac_ip_map.get(m.lower())
                        if ip:
                            current_ip = ip
                            break
            # record planned action if mismatch
            entry = {
                "tunnel_id": r["tunnel_id"],
                "route_id": route_id,
                "expected_destination": dest,
                "current_ip": current_ip,
                "planned_destination": None,
                "will_update": False,
            }

            # determine new destination preserving protocol/port/path when possible
            new_dest = None
            if current_ip:
                if isinstance(dest, str) and dest.startswith("ip:"):
                    # if probing is requested, try to detect http/https and prefer a URL
                    if probe:
                        scheme = self._probe_scheme_for_ip(current_ip, None, allow_insecure_tls)
                        if scheme in ("http", "https"):
                            new_dest = f"{scheme}://{current_ip}"
                        else:
                            new_dest = f"ip:{current_ip}"
                    else:
                        new_dest = f"ip:{current_ip}"
                else:
                    # try to parse as URL and replace hostname with current_ip
                    try:
                        parsed = urlparse(dest)
                        if parsed.scheme in ("http", "https") and parsed.hostname:
                            # preserve port if present
                            netloc = current_ip
                            if parsed.port:
                                netloc = f"{current_ip}:{parsed.port}"
                            new_parsed = parsed._replace(netloc=netloc)
                            new_dest = urlunparse(new_parsed)
                            # if probing is enabled, verify the scheme and switch if probe shows different
                            if probe:
                                probed = self._probe_scheme_for_ip(current_ip, parsed.port, allow_insecure_tls)
                                if probed and probed != parsed.scheme:
                                    # replace scheme as well
                                    new_parsed = new_parsed._replace(scheme=probed)
                                    new_dest = urlunparse(new_parsed)
                        else:
                            # fallback to ip: style
                            if probe:
                                scheme = self._probe_scheme_for_ip(current_ip, None, allow_insecure_tls)
                                if scheme in ("http", "https"):
                                    new_dest = f"{scheme}://{current_ip}"
                                else:
                                    new_dest = f"ip:{current_ip}"
                            else:
                                new_dest = f"ip:{current_ip}"
                    except Exception:
                        if probe:
                            scheme = self._probe_scheme_for_ip(current_ip, None, allow_insecure_tls)
                            if scheme in ("http", "https"):
                                new_dest = f"{scheme}://{current_ip}"
                            else:
                                new_dest = f"ip:{current_ip}"
                        else:
                            new_dest = f"ip:{current_ip}"

            entry["planned_destination"] = new_dest

            if new_dest and new_dest != dest:
                entry["will_update"] = True
                planned_changes.append(entry)
                if not dry_run:
                    # apply update
                    try:
                        self.cf.update_tunnel_route(r["tunnel_id"], route_id, new_dest)
                        # persist new ip (store only the ip part)
                        self.state.set(f"tunnel:{r['tunnel_id']}:{route_id}", current_ip)
                        print(f"Updated route {route_id} -> {new_dest}")
                    except Exception as e:
                        print(f"error updating route {route_id}: {e}")
        return planned_changes

    def _probe_scheme_for_ip(self, ip: str, port: int | None = None, allow_insecure_tls: bool = False) -> str | None:
        """Probe the given IP (and optional port) to determine if http or https responds.

        Returns 'http' or 'https' or None if neither responded.
        """
        # try HTTP
        try:
            url = f"http://{ip}"
            if port:
                url = f"http://{ip}:{port}"
            resp = requests.get(url, timeout=2, allow_redirects=False)
            # any response (including 4xx) indicates HTTP is available
            if resp.status_code >= 0:
                return "http"
        except (RequestException, ConnectionError):
            pass

        # try HTTPS
        try:
            url = f"https://{ip}"
            if port:
                url = f"https://{ip}:{port}"
            resp = requests.get(url, timeout=2, verify=not allow_insecure_tls, allow_redirects=False)
            if resp.status_code >= 0:
                return "https"
        except SSLError:
            # TLS verification failed; if allow_insecure_tls is True, try again with verify=False
            if allow_insecure_tls:
                try:
                    url = f"https://{ip}"
                    if port:
                        url = f"https://{ip}:{port}"
                    resp = requests.get(url, timeout=2, verify=False, allow_redirects=False)
                    if resp.status_code >= 0:
                        return "https"
                except RequestException:
                    pass
        except RequestException:
            pass

        return None
