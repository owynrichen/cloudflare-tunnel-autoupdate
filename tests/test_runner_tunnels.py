from proxcloud.runner import Runner
from proxcloud.state import State


class DummyCF:
    def __init__(self):
        self.updated = {}

    def update_tunnel_route(self, tunnel_id, route_id, dest):
        self.updated[route_id] = dest


def test_runner_ensure_tunnel_route(monkeypatch, tmp_path):
    state_db = str(tmp_path / 'state.db')
    s = State(state_db)
    cf = DummyCF()
    r = Runner(cf, s)

    # proxmox.get_guest_ip to return an IP
    monkeypatch.setattr('proxcloud.proxmox.get_guest_ip', lambda vm, lease_paths=None: '5.5.5.5')

    ok = r.ensure_tunnel_route('t1', 'route-1', 'vm1')
    assert ok
    assert s.get('route-1') == '5.5.5.5'
    assert cf.updated.get('route-1') == 'ip:5.5.5.5'
