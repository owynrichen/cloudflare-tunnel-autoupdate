import yaml
import importlib
cli_mod = importlib.import_module('src.cli')


def test_cli_runs_with_empty_mappings(monkeypatch, tmp_path):
    p = tmp_path / "mappings.yaml"
    p.write_text(yaml.safe_dump({"dns": [], "tunnels": []}))

    # Run main with argv (uses real load_config which reads .env in tests)
    res = cli_mod.main([str(p)])
    assert res == 0
