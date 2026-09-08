from proxcloud.runner import Runner
from proxcloud.state import State


class DummyCF:
    def __init__(self):
        self.calls = []

    def update_tunnel_route(self, tunnel_id, route_id, destination):
        self.calls.append((tunnel_id, route_id, destination))
        return {'result': {'id': route_id}}


def test_ensure_tunnel_route(monkeypatch, tmp_path):
    s = State(str(tmp_path / 'state.db'))
    cf = DummyCF()
    r = Runner(cf, s)
    # patch proxmox
    monkeypatch.setattr('proxcloud.proxmox.get_guest_ip', lambda vm, lease_paths=None: '1.2.3.4')
    ok = r.ensure_tunnel_route('t1', 'rt1', 'vm1', lease_paths=None)
    assert ok
    assert cf.calls[0][2] == 'ip:1.2.3.4'
