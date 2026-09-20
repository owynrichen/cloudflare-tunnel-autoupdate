from unittest import mock
from proxcloud.proxmox_api import ProxmoxAPI


def test_find_vm_ip_parses(monkeypatch):
    api = ProxmoxAPI("https://pm.example", "token")

    # fake cluster resources
    def fake_get(url, headers=None, timeout=None):
        class R:
            def raise_for_status(self):
                return None

            def json(self):
                if 'cluster/resources' in url:
                    return {'data': [{'vmid': '100', 'node': 'node1'}]}
                if 'network-get-interfaces' in url:
                    return {'data': {'eth0': {'ip-addresses': [{'family': 'ipv4', 'ip-address': '10.0.0.5'}]}}}
                return {'data': []}

        return R()

    monkeypatch.setattr('requests.get', fake_get)
    ip = api.find_vm_ip('100')
    assert ip == '10.0.0.5'


def test_find_vm_ip_handles_ipv6_and_cidr(monkeypatch):
    api = ProxmoxAPI("https://pm.example", "token")

    def fake_get(url, headers=None, timeout=None):
        class R:
            def raise_for_status(self):
                return None

            def json(self):
                if 'cluster/resources' in url:
                    return {'data': [{'vmid': '200', 'node': 'node2'}]}
                if 'network-get-interfaces' in url:
                    # return a list-shaped response and IPv6 with CIDR
                    return {'data': [
                        {'name': 'eth0', 'ip-addresses': [
                            {'family': 'ipv6', 'ip-address': '2001:db8::1/64'}
                        ]}
                    ]}
                return {'data': []}

        return R()

    monkeypatch.setattr('requests.get', fake_get)
    ip = api.find_vm_ip('200')
    assert ip == '2001:db8::1'
