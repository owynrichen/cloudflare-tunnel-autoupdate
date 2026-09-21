import importlib
import logging
import yaml
from pathlib import Path


def test_cli_no_args_returns_2(monkeypatch):
    cli = importlib.import_module('src.cli')
    # call with no argv uses sys.argv from pytest; pass an explicit empty list to simulate
    res = cli.main([])
    assert res == 2


def test_cli_zone_not_found_logs_error(tmp_path, monkeypatch, caplog):
    cli = importlib.import_module('src.cli')
    p = tmp_path / 'mappings.yaml'
    # create a mapping with a dns entry that will trigger missing zone id
    mappings = {'dns': [{'zone': 'nope.test', 'zone_id': None, 'record_id': 'rid', 'name': 'a.nope.test', 'type': 'A', 'vm_id': 'vm1'}], 'tunnels': []}
    p.write_text(yaml.safe_dump(mappings))

    # ensure get_zone_id will return None
    monkeypatch.setattr('src.cli.CloudflareClient.get_zone_id', lambda self, z: None)
    caplog.set_level(logging.ERROR)
    res = cli.main([str(p)])
    # should complete successfully but log an error
    assert res == 0
    assert any('zone id not found' in r.message for r in caplog.records)
