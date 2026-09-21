from proxcloud.tunnel_mapper import TunnelMapper
from proxcloud.cloudflare_client import CloudflareClient


def test_fetch_tunnel_routes_handles_missing(monkeypatch, tmp_path):
    # create mappings file referencing a tunnel id that will 404
    p = tmp_path / 'm.yaml'
    p.write_text('tunnels:\n  - tunnel_id: bad-tunnel\n    route_id: r1\n    vm_id: vm1\n')

    tm = TunnelMapper(str(p))
    # monkeypatch CloudflareClient.list_tunnel_routes to raise
    monkeypatch.setattr(CloudflareClient, 'list_tunnel_routes', lambda self, tid: (_ for _ in ()).throw(Exception('404')))
    routes = tm.fetch_tunnel_routes()
    assert routes == []
