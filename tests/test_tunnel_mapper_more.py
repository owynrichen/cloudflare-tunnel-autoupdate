import yaml

from src.proxcloud.tunnel_mapper import TunnelMapper
from src.proxcloud.cloudflare_client import CloudflareClient
from src.proxcloud.proxmox_api import ProxmoxAPI


def test_https_preserve(monkeypatch, tmp_path):
    # https scheme should be preserved and hostname replaced with IP
    def fake_list_tunnel_routes(self, tid):
        return {"result": [{"id": "r1", "destination": "https://service.local:8443/api/v1"}]}

    monkeypatch.setattr(CloudflareClient, "list_tunnel_routes", fake_list_tunnel_routes)
    mapping = {"tunnels": [{"tunnel_id": "t1", "route_id": "r1", "vm_id": "vmA"}]}
    p = tmp_path / "mappings.yaml"
    p.write_text(yaml.safe_dump(mapping))
    monkeypatch.setattr(ProxmoxAPI, "find_vm_ip", lambda self, vmid: "172.16.0.9")

    tm = TunnelMapper(str(p))
    planned = tm.ensure_mappings(dry_run=True)
    assert len(planned) == 1
    dest = planned[0]["planned_destination"]
    assert dest.startswith("https://172.16.0.9")
    assert ":8443" in dest
    assert dest.endswith("/api/v1")


def test_tcp_fallback_to_ip(monkeypatch, tmp_path):
    # non-http(s) schemes should fall back to ip:<ip>
    def fake_list_tunnel_routes(self, tid):
        return {"result": [{"id": "r2", "destination": "tcp://somehost:22"}]}

    monkeypatch.setattr(CloudflareClient, "list_tunnel_routes", fake_list_tunnel_routes)
    mapping = {"tunnels": [{"tunnel_id": "t2", "route_id": "r2", "vm_id": "vmB"}]}
    p = tmp_path / "mappings.yaml"
    p.write_text(yaml.safe_dump(mapping))
    monkeypatch.setattr(ProxmoxAPI, "find_vm_ip", lambda self, vmid: "10.10.10.10")

    tm = TunnelMapper(str(p))
    planned = tm.ensure_mappings(dry_run=True)
    assert len(planned) == 1
    assert planned[0]["planned_destination"] == "ip:10.10.10.10"


def test_no_change_if_same_ip(monkeypatch, tmp_path):
    # if destination already ip: matches current IP, no planned change
    def fake_list_tunnel_routes(self, tid):
        return {"result": [{"id": "r3", "destination": "ip:10.0.0.5"}]}

    monkeypatch.setattr(CloudflareClient, "list_tunnel_routes", fake_list_tunnel_routes)
    mapping = {"tunnels": [{"tunnel_id": "t3", "route_id": "r3", "vm_id": "vmC"}]}
    p = tmp_path / "mappings.yaml"
    p.write_text(yaml.safe_dump(mapping))
    monkeypatch.setattr(ProxmoxAPI, "find_vm_ip", lambda self, vmid: "10.0.0.5")

    tm = TunnelMapper(str(p))
    planned = tm.ensure_mappings(dry_run=True)
    assert len(planned) == 0
