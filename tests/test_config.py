import os
from importlib import reload

def test_load_config_env(monkeypatch):
    # set env vars and reload module to ensure load_dotenv took effect
    monkeypatch.setenv('CLOUDFLARE_API_TOKEN', 'tk')
    monkeypatch.setenv('CLOUDFLARE_ACCOUNT_ID', 'acct')
    # import here to avoid import-time failures elsewhere
    import proxcloud.config as config
    reload(config)
    cfg = config.load_config()
    assert cfg.cloudflare_token == 'tk'
    assert cfg.cloudflare_account == 'acct'
