import pytest
from proxcloud.cloudflare_client import CloudflareClient
from unittest import mock


def test_get_zone_id_parses(monkeypatch):
    client = CloudflareClient("tk", "acct")

    class DummyResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"result": [{"id": "zone-1"}]}

    monkeypatch.setattr("requests.get", lambda *a, **k: DummyResp())
    assert client.get_zone_id("example.com") == "zone-1"


def test_tunnel_update_calls_put(monkeypatch):
    client = CloudflareClient("tk", "acct")

    class DummyResp2:
        def raise_for_status(self):
            pass

        def json(self):
            return {"result": [{"id": "r1", "destination": "ip:1.2.3.4"}]}

    def dummy_get(*a, **k):
        return DummyResp2()

    monkeypatch.setattr("requests.get", dummy_get)
    res = client.list_tunnel_routes("tid")
    assert res["result"][0]["destination"] == "ip:1.2.3.4"
