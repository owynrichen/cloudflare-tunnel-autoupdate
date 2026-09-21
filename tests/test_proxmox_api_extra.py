from proxcloud.proxmox_api import ProxmoxAPI


def test_base_url_normalization():
    api = ProxmoxAPI('https://host:8006/api2/json', 'tok')
    assert api.base == 'https://host:8006'


def test_get_vm_interfaces_forced_types(monkeypatch):
    api = ProxmoxAPI('https://pm.example', 'token')

    urls = []

    def fake_get(url, headers=None, timeout=None, verify=True):
        urls.append(url)

        class R:
            def raise_for_status(self):
                return None

            def json(self):
                return {'data': {'eth0': {'ip-addresses': [{'family': 'ipv4', 'ip-address': '10.0.0.7'}]}}}

        return R()

    monkeypatch.setattr('requests.get', fake_get)
    # force qemu
    d = api.get_vm_interfaces('node1', '10', vm_type='qemu')
    assert d is not None
    assert any('/qemu/' in u for u in urls)

    urls.clear()
    d = api.get_vm_interfaces('node1', '10', vm_type='lxc')
    assert d is not None
    assert any('/lxc/' in u for u in urls)


def test_get_vm_config_none(monkeypatch):
    api = ProxmoxAPI('https://pm.example', 'token')

    def fake_get(url, headers=None, timeout=None, verify=True):
        class R:
            def raise_for_status(self):
                return None

            def json(self):
                return {'data': None}

        return R()

    monkeypatch.setattr('requests.get', fake_get)
    assert api.get_vm_config('n', '1') is None


def test_ip_from_config_name_fallback(monkeypatch):
    api = ProxmoxAPI('https://pm.example', 'token')
    cfg = {'net0': 'virtio=11:22:33:44:55:66,bridge=vmbr0', 'name': 'host123'}

    # make find_ip_for return by name
    monkeypatch.setattr('proxcloud.proxmox_api.find_ip_for', lambda ident: '7.7.7.7' if ident == 'host123' else None)
    ip = api._ip_from_config_or_leases(cfg, '1')
    assert ip == '7.7.7.7'
