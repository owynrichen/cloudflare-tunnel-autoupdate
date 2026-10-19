import yaml

from src.proxcloud.tunnel_mapper import TunnelMapper
from src.proxcloud.cloudflare_client import CloudflareClient
from src.proxcloud.proxmox_api import ProxmoxAPI


def test_url_preserve(monkeypatch, tmp_path):
    # cloudflare returns a route with http scheme, port and path
    def fake_list_tunnel_routes(self, tid):
        return {"result": [{"id": "r1", "destination": "http://example.local:8080/svc"}]}

    monkeypatch.setattr(CloudflareClient, "list_tunnel_routes", fake_list_tunnel_routes)

    mapping = {"tunnels": [{"tunnel_id": "t1", "route_id": "r1", "vm_id": "vm123"}]}
    p = tmp_path / "mappings.yaml"
    p.write_text(yaml.safe_dump(mapping))

    # proxmox returns an IP for the VM
    monkeypatch.setattr(ProxmoxAPI, "find_vm_ip", lambda self, vmid: "10.0.0.55")

    tm = TunnelMapper(str(p))
    planned = tm.ensure_mappings(dry_run=True)

    assert len(planned) == 1
    planned_dest = planned[0]["planned_destination"]
    assert planned_dest.startswith("http://10.0.0.55")
    assert planned_dest.endswith("/svc")
    assert ":8080" in planned_dest
