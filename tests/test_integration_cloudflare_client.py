import json
from proxcloud.cloudflare_client import CloudflareClient


class DummyResp:
    def __init__(self, data=None):
        self._data = data or {"result": []}

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


def test_update_dns_puts_correct_payload(monkeypatch):
    client = CloudflareClient("tk", "acct")
    captured = {}

    def fake_put(url, json=None, headers=None):
        captured['url'] = url
        captured['json'] = json
        return DummyResp({"result": {"id": "rid-1"}})

    monkeypatch.setattr("requests.put", fake_put)
    res = client.update_dns("zone-1", "rid-1", "host.example.com", "A", "1.2.3.4")
    assert "zones/zone-1/dns_records/rid-1" in captured['url']
    assert captured['json'] == {"type": "A", "name": "host.example.com", "content": "1.2.3.4"}


def test_update_tunnel_route_puts_correct_payload(monkeypatch):
    client = CloudflareClient("tk", "acct")
    captured = {}

    def fake_put(url, json=None, headers=None):
        captured['url'] = url
        captured['json'] = json
        return DummyResp({"result": {"id": "route-1"}})

    monkeypatch.setattr("requests.put", fake_put)
    res = client.update_tunnel_route("tunnel-1", "route-1", "ip:5.6.7.8")
    assert "/accounts/acct/tunnels/tunnel-1/routes/route-1" in captured['url']
    assert captured['json'] == {"destination": "ip:5.6.7.8"}
