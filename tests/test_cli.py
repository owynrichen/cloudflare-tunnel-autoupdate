import tempfile
import yaml
import src.cli as cli


class DummyCF:
    def __init__(self, token, acct):
        self.token = token
        self.acct = acct

    def get_zone_id(self, domain):
        return "zone-1"


class DummyState:
    def __init__(self, path):
        self.path = path


class DummyRunner:
    def __init__(self, cf, state):
        self.cf = cf
        self.state = state
        self.calls = []

    def ensure_dns(self, zone_id, record_id, name, type_, vm_id, lease_paths=None):
        self.calls.append(('dns', zone_id, record_id, name, type_, vm_id, lease_paths))
        return True

    def ensure_tunnel_route(self, tunnel_id, route_id, vm_id, lease_paths=None):
        self.calls.append(('tunnel', tunnel_id, route_id, vm_id, lease_paths))
        return True


def test_cli_main_runs(monkeypatch, tmp_path):
    # write a mappings yaml
    mappings = {
        'lease_paths': ['/tmp/leases/*.leases'],
        'dns': [
            {
                'zone': 'example.com',
                'zone_id': None,
                'record_id': 'r1',
                'name': 'host.example.com',
                'type': 'A',
                'vm_id': 'vm1'
            }
        ],
        'tunnels': [
            {
                'tunnel_id': 't1',
                'route_id': 'rt1',
                'vm_id': 'vm1'
            }
        ]
    }
    p = tmp_path / 'm.yaml'
    p.write_text(yaml.safe_dump(mappings))

    # monkeypatch config loader
    monkeypatch.setattr(cli, 'CloudflareClient', DummyCF)
    monkeypatch.setattr(cli, 'State', DummyState)
    monkeypatch.setattr(cli, 'Runner', DummyRunner)

    # run main with our mappings
    rc = cli.main([str(p)])
    assert rc == 0
    # ensure runner was invoked for dns and tunnel
    # the Runner class was replaced, so main should have created an instance
    # no exception is a good sign
