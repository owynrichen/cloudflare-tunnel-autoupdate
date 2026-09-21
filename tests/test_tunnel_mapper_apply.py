import yaml
from pathlib import Path
from proxcloud.tunnel_mapper import TunnelMapper
from proxcloud.cloudflare_client import CloudflareClient
from proxcloud.proxmox_api import ProxmoxAPI


def test_ensure_mappings_apply(monkeypatch, tmp_path):
    # prepare mappings file
    mapping = {"tunnels": [{"tunnel_id": "t1", "route_id": "r1", "vm_id": "vm123"}]}
    p = tmp_path / "mappings.yaml"
    p.write_text(yaml.safe_dump(mapping))

    # mock cloudflare to return a route with expected ip
    def fake_list_tunnel_routes(self, tid):
        return {"result": [{"id": "r1", "destination": "ip:1.1.1.1"}]}

    updated = {}

    def fake_update_tunnel_route(self, tunnel_id, route_id, destination):
        updated[route_id] = destination
        return {"result": True}

    monkeypatch.setattr(CloudflareClient, "list_tunnel_routes", fake_list_tunnel_routes)
    monkeypatch.setattr(CloudflareClient, "update_tunnel_route", fake_update_tunnel_route)

    # proxmox returns a different ip
    monkeypatch.setattr(ProxmoxAPI, "find_vm_ip", lambda self, vmid: "2.2.2.2")

    # run mapper with a fresh state DB
    state_db = str(tmp_path / "state.db")
    tm = TunnelMapper(str(p), state_db=state_db)
    planned = tm.ensure_mappings(dry_run=False)

    # ensure_update applied
    assert any(item["will_update"] for item in planned)
    # state should have been set
    assert tm.state.get("tunnel:t1:r1") == "2.2.2.2"
    assert updated.get("r1") == "ip:2.2.2.2"


def test_ensure_mappings_mac_fallback(monkeypatch, tmp_path):
    mapping = {"tunnels": [{"tunnel_id": "t2", "route_id": "r2", "vm_id": "vm999"}]}
    p = tmp_path / "mappings2.yaml"
    p.write_text(yaml.safe_dump(mapping))

    # cloudflare returns expected ip
    monkeypatch.setattr(CloudflareClient, "list_tunnel_routes", lambda self, tid: {"result": [{"id": "r2", "destination": "ip:3.3.3.3"}]})

    # proxmox find_vm_ip returns None so fallback should be used
    monkeypatch.setattr(ProxmoxAPI, "find_vm_ip", lambda self, vmid: None)
    # proxmox get_vm_config returns config with a MAC
    monkeypatch.setattr(ProxmoxAPI, "get_vm_config", lambda self, node, vmid: {"net0": "virtio=AA:BB:CC:DD:EE:11,bridge=vmbr0"})

    # provide a mac_ip_map mapping the mac to an ip
    mac_map = {"aa:bb:cc:dd:ee:11": "4.4.4.4"}

    tm = TunnelMapper(str(p), state_db=str(tmp_path / "state2.db"))
    planned = tm.ensure_mappings(dry_run=True, mac_ip_map=mac_map)
    assert len(planned) == 1
    assert planned[0]["current_ip"] == "4.4.4.4"
