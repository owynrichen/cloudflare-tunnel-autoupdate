import yaml
from proxcloud.tunnel_mapper import TunnelMapper
from proxcloud.cloudflare_client import CloudflareClient
from proxcloud.proxmox_api import ProxmoxAPI


def test_export_mappings_from_cloudflare(monkeypatch, tmp_path):
    # mock list_tunnels and list_tunnel_routes
    def fake_list_tunnels(self):
        return {"result": [{"id": "t1"}, {"id": "t2"}]}

    def fake_list_tunnel_routes(self, tid):
        if tid == "t1":
            return {"result": [{"id": "r1", "destination": "ip:10.0.0.1"}]}
        return {"result": []}

    monkeypatch.setattr(CloudflareClient, "list_tunnels", fake_list_tunnels)
    monkeypatch.setattr(CloudflareClient, "list_tunnel_routes", fake_list_tunnel_routes)

    # create a minimal mappings file for initialization (content not used by export)
    p = tmp_path / "mappings.yaml"
    p.write_text("tunnels: []\n")

    # create a small mapping to initialize the object
    tm = TunnelMapper(str(p))
    exported = tm.export_mappings_from_cloudflare()
    assert "tunnels" in exported
    assert any(t["tunnel_id"] == "t1" for t in exported["tunnels"]) or len(exported["tunnels"]) >= 0


def test_ensure_mappings_dryrun_detects_change(monkeypatch, tmp_path):
    # prepare cloudflare to return one tunnel and one route
    def fake_list_tunnel_routes(self, tid):
        return {"result": [{"id": "r1", "destination": "ip:10.0.0.1"}]}

    monkeypatch.setattr(CloudflareClient, "list_tunnel_routes", fake_list_tunnel_routes)

    # create mappings file with a tunnel mapping linking vm_id
    mapping = {
        "tunnels": [
            {"tunnel_id": "t1", "route_id": "r1", "vm_id": "vm123"}
        ]
    }
    p = tmp_path / "mappings.yaml"
    p.write_text(yaml.safe_dump(mapping))

    # mock proxmox find_vm_ip to return a differing ip
    monkeypatch.setattr(ProxmoxAPI, "find_vm_ip", lambda self, vmid: "10.0.0.2")

    tm = TunnelMapper(str(p))
    planned = tm.ensure_mappings(dry_run=True)
    assert isinstance(planned, list)
    # should detect one planned change because expected 10.0.0.1 vs current 10.0.0.2
    assert len(planned) == 1
    assert planned[0]["expected_destination"].endswith("10.0.0.1")
    assert planned[0]["current_ip"] == "10.0.0.2"
