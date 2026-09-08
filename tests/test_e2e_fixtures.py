import json
import os
import pathlib
import pytest

from proxcloud.cloudflare_client import CloudflareClient
from proxcloud.state import State
from proxcloud.runner import Runner


def _load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def _fixture_path():
    p = pathlib.Path("tests/production_fixtures")
    # Require the directory and primary zones.json file to exist. If the sanitized
    # fixtures aren't present in the repo (e.g. on a PR), skip the e2e fixture test.
    zones_file = p / "zones.json"
    if not p.exists() or not zones_file.exists():
        pytest.skip("No production fixtures found (tests/production_fixtures/zones.json) — skipping e2e fixture test")
    return p


def test_runner_with_fixtures(monkeypatch, tmp_path):
    p = _fixture_path()
    zones = _load_json(p / "zones.json")
    results = zones.get("result", [])
    if not results:
        pytest.skip("No zones in fixtures")

    zone = results[0]
    zone_id = zone.get("id")

    dns_file = p / f"dns_{zone_id}.json"
    if not dns_file.exists():
        pytest.skip(f"No dns fixture for zone {zone_id}")

    dns = _load_json(dns_file)
    recs = dns.get("result", [])
    if not recs:
        pytest.skip("No dns records in fixtures")

    # Prepare client and state
    client = CloudflareClient("tk", "acct")
    s = State(str(tmp_path / "state.db"))

    # Monkeypatch requests.get to return fixture data depending on URL
    def fake_get(url, headers=None, params=None, timeout=None):
        class R:
            def __init__(self, data):
                self._data = data

            def raise_for_status(self):
                return None

            def json(self):
                return self._data

        if "/zones" in url and "dns_records" not in url:
            return R(zones)
        if f"/zones/{zone_id}/dns_records" in url:
            return R(dns)
        if "/accounts/" in url and "/tunnels" in url:
            tunnels = _load_json(p / "tunnels.json") if (p / "tunnels.json").exists() else {"result": []}
            return R(tunnels)
        return R({"result": []})

    monkeypatch.setattr("requests.get", fake_get)

    # capture PUTs
    captured = {}

    def fake_put(url, json=None, headers=None, timeout=None):
        captured['url'] = url
        captured['json'] = json
        class R:
            def raise_for_status(self):
                return None

            def json(self):
                return {"result": {"id": "ok"}}

        return R()

    monkeypatch.setattr("requests.put", fake_put)

    r = Runner(client, s)

    # Use the first dns record in fixture
    rec = recs[0]
    record_id = rec.get("id")
    name = rec.get("name")
    type_ = rec.get("type")

    # patch proxmox to return a new ip
    monkeypatch.setattr("proxcloud.proxmox.get_guest_ip", lambda vm, lease_paths=None: "9.9.9.9")

    ok = r.ensure_dns(zone_id, record_id, name, type_, "vm1", lease_paths=None)
    assert ok
    assert captured['json']['content'] == "9.9.9.9"
