import tempfile
import yaml
from proxcloud.mapping import load_mappings


def test_load_mappings_injects_global(tmp_path):
    cfg = {
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
    p.write_text(yaml.safe_dump(cfg))
    m = load_mappings(str(p))
    assert len(m.dns) == 1
    assert m.dns[0].lease_paths == ['/tmp/leases/*.leases']
    assert len(m.tunnels) == 1
    assert m.tunnels[0].lease_paths == ['/tmp/leases/*.leases']
