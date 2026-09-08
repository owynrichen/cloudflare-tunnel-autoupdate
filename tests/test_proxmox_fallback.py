import tempfile
import os
from proxcloud.proxmox import get_guest_ip


def test_proxmox_api_fallback_to_dhcp(monkeypatch, tmp_path):
    # create a fake isc dhcp lease file
    p = tmp_path / "dhcpd.leases"
    p.write_text("lease 10.0.0.7 { hardware ethernet 11:22:33:44:55:66; client-hostname \"vm3\"; }")

    # force proxmox API to be used but return None
    monkeypatch.setenv("PROXMOX_API_URL", "https://pm.example")
    monkeypatch.setenv("PROXMOX_API_TOKEN", "token")

    # monkeypatch the ProxmoxAPI.find_vm_ip to return None, forcing fallback
    import proxcloud.proxmox_api as api_mod

    monkeypatch.setattr(api_mod.ProxmoxAPI, "find_vm_ip", lambda self, vmid: None)

    ip = get_guest_ip("vm3", lease_paths=[str(p)])
    assert ip == "10.0.0.7"
