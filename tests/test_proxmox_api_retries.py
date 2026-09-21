from proxcloud.proxmox_api import ProxmoxAPI


def test__get_retries_eventual_success(monkeypatch):
    api = ProxmoxAPI('https://pm.example', 'token')
    calls = {'n': 0}

    class R:
        def raise_for_status(self):
            return None

        def json(self):
            return {'data': []}

    def fake_get(url, headers=None, timeout=None, verify=True):
        calls['n'] += 1
        if calls['n'] < 3:
            raise RuntimeError('transient')
        return R()

    monkeypatch.setattr('requests.get', fake_get)
    r = api._get('https://pm.example/api2/json/cluster/resources')
    assert r is not None
    assert calls['n'] == 3
