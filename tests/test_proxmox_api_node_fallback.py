from proxcloud.proxmox_api import ProxmoxAPI
import proxcloud.proxmox_api as pmod


def test_find_vm_ip_node_fallback_to_config(monkeypatch):
    api = ProxmoxAPI('https://pm.example', 'token')

    # simulate network-get-interfaces returning None (no agent data)
    def fake_get(url, headers=None, timeout=None, verify=True):
        class R:
            def raise_for_status(self):
                return None

            def json(self):
                # simulate network-get-interfaces endpoint returning {'data': None}
                if 'network-get-interfaces' in url:
                    return {'data': None}
                return {'data': []}

        return R()

    monkeypatch.setattr('requests.get', fake_get)

    # monkeypatch get_vm_config to return a config with a MAC
    monkeypatch.setattr(pmod.ProxmoxAPI, 'get_vm_config', lambda self, node, vmid: {'net0': 'virtio=AA:BB:CC:DD:EE:99,bridge=vmbr0', 'name': 'fallback'})

    # monkeypatch find_ip_for to map mac to ip
    monkeypatch.setattr('proxcloud.proxmox_api.find_ip_for', lambda m: '9.9.9.9' if m.lower().startswith('aa:bb') else None)

    ip = api.find_vm_ip('500@nodeA')
    assert ip == '9.9.9.9'
