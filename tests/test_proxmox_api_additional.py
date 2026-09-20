from proxcloud.proxmox_api import ProxmoxAPI


def test_find_vm_ip_with_node_shortcut(monkeypatch):
    api = ProxmoxAPI("https://pm.example", "token")

    def fake_get(url, headers=None, timeout=None):
        class R:
            def raise_for_status(self):
                return None

            def json(self):
                if 'network-get-interfaces' in url:
                    return {'data': {'eth0': {'ip-addresses': [{'family': 'ipv4', 'ip-address': '10.0.0.9'}]}}}
                return {'data': []}

        return R()

    monkeypatch.setattr('requests.get', fake_get)
    # include node in vmid
    ip = api.find_vm_ip('123@nodeA')
    assert ip == '10.0.0.9'


def test_find_vm_ip_lxc_response(monkeypatch):
    api = ProxmoxAPI("https://pm.example", "token")

    def fake_get(url, headers=None, timeout=None):
        class R:
            def raise_for_status(self):
                return None

            def json(self):
                if 'cluster/resources' in url:
                    return {'data': [{'vmid': '300', 'node': 'nodeLXC', 'type': 'lxc'}]}
                if '/lxc/' in url and 'network-get-interfaces' in url:
                    return {'data': {'eth0': {'ip-addresses': [{'family': 'ipv4', 'ip-address': '172.16.0.7/24'}]}}}
                return {'data': []}

        return R()

    monkeypatch.setattr('requests.get', fake_get)
    ip = api.find_vm_ip('300')
    assert ip == '172.16.0.7'


def test_find_vm_ip_handles_api_error(monkeypatch):
    api = ProxmoxAPI("https://pm.example", "token")

    def fake_get(url, headers=None, timeout=None):
        raise Exception("network down")

    monkeypatch.setattr('requests.get', fake_get)
    ip = api.find_vm_ip('999')
    assert ip is None
