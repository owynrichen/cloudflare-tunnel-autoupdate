import pytest


def pytest_configure(config):
    # ensure tests don't pick up real env state accidentally
    import os
    os.environ.pop("CLOUDFLARE_API_TOKEN", None)
    os.environ.pop("CLOUDFLARE_ACCOUNT_ID", None)
    # ensure STATE_DB doesn't accidentally point to production
    os.environ.pop("STATE_DB", None)
    # set fake cloudflare creds for tests that import config
    os.environ.setdefault("CLOUDFLARE_API_TOKEN", "test-token")
    os.environ.setdefault("CLOUDFLARE_ACCOUNT_ID", "test-account")
    # ensure local src is importable as a package
    import sys
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1]
    src = str(root / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
