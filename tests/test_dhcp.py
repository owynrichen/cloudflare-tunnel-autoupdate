from proxcloud.dhcp import _parse_isc_leases, _parse_dnsmasq_leases, find_ip_for
import tempfile
import os


def test_parse_isc():
    content = """
lease 10.0.0.5 {
  starts 5 2020/01/01 00:00:00;
  hardware ethernet aa:bb:cc:dd:ee:ff;
  client-hostname "vm1";
}
"""
    leases = _parse_isc_leases(content)
    assert "10.0.0.5" in leases
    assert leases["10.0.0.5"]["mac"] == "aa:bb:cc:dd:ee:ff"


def test_parse_dnsmasq():
    content = "159238 aa:bb:cc:dd:ee:ff 10.0.0.6 vm2 *"
    leases = _parse_dnsmasq_leases(content)
    assert "10.0.0.6" in leases
    assert leases["10.0.0.6"]["mac"] == "aa:bb:cc:dd:ee:ff"


def test_find_ip_for(tmp_path, monkeypatch):
    # create a fake lease file
    d = tmp_path / "dhcp"
    d.mkdir()
    p = d / "dhcpd.leases"
    p.write_text("lease 10.0.0.7 { hardware ethernet 11:22:33:44:55:66; client-hostname \"vm3\"; }")

    monkeypatch.setattr("glob.glob", lambda pattern: [str(p)])
    assert find_ip_for("11:22:33:44:55:66", lease_paths=[str(p)]) == "10.0.0.7"
    assert find_ip_for("vm3", lease_paths=[str(p)]) == "10.0.0.7"
