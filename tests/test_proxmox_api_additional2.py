import json
from proxcloud.proxmox_api import ProxmoxAPI
from proxcloud import proxmox_api


def test_get_vm_interfaces_try_both(monkeypatch):
    api = ProxmoxAPI("https://pm.example", "token")

    calls = []

    def fake_get(url, headers=None, timeout=None, verify=True):
        calls.append(url)

        class R:
            def raise_for_status(self):
                return None

            def json(self):
                if '/qemu/' in url:
                    # simulate agent not present
                    raise ValueError('no json')
                if '/lxc/' in url:
                    return {'data': {'eth0': {'ip-addresses': [{'family': 'ipv4', 'ip-address': '10.1.2.3'}]}}}
                return {'data': []}

        return R()

    monkeypatch.setattr('requests.get', fake_get)
    data = api.get_vm_interfaces('node1', '42')
    assert data is not None
    # should have tried qemu then lxc
    assert any('/qemu/' in c for c in calls)
    assert any('/lxc/' in c for c in calls)


def test_find_vm_ip_cluster_and_ipv6(monkeypatch):
    api = ProxmoxAPI('https://pm.example', 'token')

    def fake_get(url, headers=None, timeout=None, verify=True):
        class R:
            def raise_for_status(self):
                return None

            def json(self):
                if 'cluster/resources' in url:
                    return {'data': [{'vmid': '200', 'node': 'node2'}]}
                if 'network-get-interfaces' in url:
                    return {'data': [
                        {'name': 'eth0', 'ip-addresses': [{'family': 'ipv6', 'ip-address': '2001:db8::2/64'}]}
                    ]}
                return {'data': []}

        return R()

    monkeypatch.setattr('requests.get', fake_get)
    ip = api.find_vm_ip('200')
    assert ip == '2001:db8::2'


def test_get_vm_config_tries_qemu_then_lxc(monkeypatch):
    api = ProxmoxAPI('https://pm.example', 'token')

    def fake_get(url, headers=None, timeout=None, verify=True):
        class R:
            def raise_for_status(self):
                return None

            def json(self):
                if '/qemu/' in url:
                    # simulate 500-like failure by returning None data
                    return {'data': None}
                if '/lxc/' in url:
                    return {'data': {'net0': 'name=eth0,hwaddr=aa:bb:cc:dd:ee:ff'}}
                return {'data': []}

        return R()

    monkeypatch.setattr('requests.get', fake_get)
    cfg = api.get_vm_config('node1', '10')
    assert cfg is not None
    assert 'net0' in cfg


def test_ip_from_config_or_leases_uses_find_ip_for(monkeypatch):
    api = ProxmoxAPI('https://pm.example', 'token')
    cfg = {'net0': 'virtio=AA:BB:CC:DD:EE:FF,bridge=vmbr0', 'name': 'myvm'}

    # monkeypatch find_ip_for to return by mac
    monkeypatch.setattr('proxcloud.proxmox_api.find_ip_for', lambda mac: '10.10.10.5' if mac.lower().startswith('aa:') else None)
    ip = api._ip_from_config_or_leases(cfg, '10')
    assert ip == '10.10.10.5'
