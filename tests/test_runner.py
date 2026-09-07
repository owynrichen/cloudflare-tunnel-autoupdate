import tempfile
import os
from unittest import mock
from proxcloud.state import State
from proxcloud.runner import Runner


class DummyCF:
    def __init__(self):
        self.calls = []

    def update_dns(self, zone_id, record_id, name, type_, content):
        self.calls.append((zone_id, record_id, name, type_, content))
        return {"success": True}


def test_runner_updates(monkeypatch):
    fd, path = tempfile.mkstemp()
    os.close(fd)
    s = State(path)
    cf = DummyCF()
    r = Runner(cf, s)

    # patch proxmox.get_guest_ip
    monkeypatch.setattr("proxcloud.proxmox.get_guest_ip", lambda vm, lease_paths=None: "10.0.0.5")

    ok = r.ensure_dns("z1", "rid-1", "host.example.com", "A", "vm1", lease_paths=None)
    assert ok
    assert s.get("rid-1") == "10.0.0.5"
    assert cf.calls[0][4] == "10.0.0.5"

    # second call with same IP should not call update
    cf.calls.clear()
    ok = r.ensure_dns("z1", "rid-1", "host.example.com", "A", "vm1", lease_paths=None)
    assert ok
    assert cf.calls == []

    s.close()
    os.remove(path)
