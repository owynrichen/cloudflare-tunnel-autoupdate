import types
import pytest
from proxcloud.proxmox_api import ProxmoxAPI


def make_cfg(token_id=None, verify=True):
    cfg = types.SimpleNamespace()
    cfg.proxmox_api_token_id = token_id
    cfg.proxmox_api_verify = verify
    return cfg


def test_header_construction_with_token_id(monkeypatch):
    # ensure load_config returns a token id so header is constructed properly
    monkeypatch.setattr('proxcloud.proxmox_api.load_config', lambda: make_cfg(token_id='user@pam!id'))
    api = ProxmoxAPI('https://pm.example', 'secret')
    assert 'PVEAPIToken=user@pam!id=secret' in api.headers.get('Authorization')


def test_header_uses_full_token_if_provided(monkeypatch):
    monkeypatch.setattr('proxcloud.proxmox_api.load_config', lambda: make_cfg(token_id=None))
    api = ProxmoxAPI('https://pm.example', 'PVEAPIToken=full=tok')
    assert api.headers.get('Authorization') == 'PVEAPIToken=full=tok'


def test_get_retries_and_handles_typeerror(monkeypatch):
    api = ProxmoxAPI('https://pm.example', 'token')

    calls = {'count': 0}

    class Dummy:
        def raise_for_status(self):
            return None

        def json(self):
            return {'data': []}

    def fake_get_with_verify(url, headers=None, timeout=None, verify=True):
        calls['count'] += 1
        raise TypeError('verify not supported')

    def fake_get_no_verify(url, headers=None, timeout=None):
        calls['count'] += 1
        return Dummy()

    # first call with verify raises TypeError; second call without verify succeeds
    monkeypatch.setattr('requests.get', fake_get_with_verify)
    # monkeypatch second call path by swapping behavior after first call
    def wrapper(url, headers=None, timeout=None, verify=True):
        if calls['count'] == 0:
            return fake_get_with_verify(url, headers=headers, timeout=timeout, verify=verify)
        return fake_get_no_verify(url, headers=headers, timeout=timeout)

    monkeypatch.setattr('requests.get', wrapper)
    r = api._get('https://pm.example/api2/json/cluster/resources')
    assert r is not None


def test_get_handles_network_exception(monkeypatch):
    api = ProxmoxAPI('https://pm.example', 'token')

    def bad_get(url, headers=None, timeout=None, verify=True):
        raise RuntimeError('network')

    monkeypatch.setattr('requests.get', bad_get)
    r = api._get('https://pm.example/api2/json/cluster/resources')
    assert r is None


def test_init_when_load_config_raises(monkeypatch):
    # simulate load_config raising so __init__ falls back
    monkeypatch.setattr('proxcloud.proxmox_api.load_config', lambda: (_ for _ in ()).throw(RuntimeError('no env')))
    api = ProxmoxAPI('https://pm.example/api2/json', 'abc-token')
    # header should be constructed from token since token_id not available
    assert api.headers.get('Authorization') == 'PVEAPIToken=abc-token'
    # verify should default to True when load_config fails
    assert api.verify is True
