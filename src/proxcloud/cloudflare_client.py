import requests
from typing import Optional, Dict, Any


class CloudflareClient:
    def __init__(self, api_token: str, account_id: str):
        self.api_token = api_token
        self.account_id = account_id
        self.base = "https://api.cloudflare.com/client/v4"
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    def _get(self, path: str, params: Dict[str, str] | None = None) -> Dict[str, Any]:
        url = f"{self.base}{path}"
        r = requests.get(url, headers=self.headers, params=params)
        r.raise_for_status()
        return r.json()

    def _put(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base}{path}"
        r = requests.put(url, json=body, headers=self.headers)
        r.raise_for_status()
        return r.json()

    def get_zone_id(self, domain: str) -> Optional[str]:
        data = self._get("/zones", params={"name": domain})
        res = data.get("result", [])
        return res[0]["id"] if len(res) > 0 else None

    def list_dns(self, zone_id: str) -> Dict[str, Any]:
        return self._get(f"/zones/{zone_id}/dns_records")

    def update_dns(self, zone_id: str, record_id: str, name: str, type_: str, content: str) -> Dict[str, Any]:
        return self._put(f"/zones/{zone_id}/dns_records/{record_id}", {"type": type_, "name": name, "content": content})

    # Cloudflare Tunnels API: list routes for a tunnel, update an ip route
    def list_tunnel_routes(self, tunnel_id: str) -> Dict[str, Any]:
        return self._get(f"/accounts/{self.account_id}/tunnels/{tunnel_id}/routes")

    def update_tunnel_route(self, tunnel_id: str, route_id: str, destination: str) -> Dict[str, Any]:
        # destination is like "ip:1.2.3.4"
        return self._put(f"/accounts/{self.account_id}/tunnels/{tunnel_id}/routes/{route_id}", {"destination": destination})
