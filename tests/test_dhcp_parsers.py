from proxcloud.dhcp import _parse_isc_leases, _parse_dnsmasq_leases, find_ip_for
import tempfile


def test_parse_isc_leases_and_find_ip(tmp_path):
    content = '''lease 192.168.1.50 {
  starts 3 2023/01/01 00:00:00;
  ends 3 2023/01/01 01:00:00;
  hardware ethernet aa:bb:cc:dd:ee:ff;
  client-hostname "myvm";
}
'''
    # parse directly
    leases = _parse_isc_leases(content)
    assert '192.168.1.50' in leases
    assert leases['192.168.1.50']['mac'].lower() == 'aa:bb:cc:dd:ee:ff'
    assert leases['192.168.1.50']['name'] == 'myvm'

    # write to a temporary file and use find_ip_for with explicit path
    p = tmp_path / 'dhcpd.leases'
    p.write_text(content)
    ip = find_ip_for('myvm', lease_paths=[str(p)])
    assert ip == '192.168.1.50'


def test_parse_dnsmasq_and_find_ip(tmp_path):
    content = '1678888888 aa:bb:cc:11:22:33 192.168.1.60 host1 *\n'
    leases = _parse_dnsmasq_leases(content)
    assert '192.168.1.60' in leases
    assert leases['192.168.1.60']['mac'] == 'aa:bb:cc:11:22:33'

    p = tmp_path / 'dnsmasq.leases'
    p.write_text(content)
    ip = find_ip_for('aa:bb:cc:11:22:33', lease_paths=[str(p)])
    assert ip == '192.168.1.60'
