"""Validate a Cloudflare API token has the likely required permissions.

This script performs safe read calls and reports HTTP status codes for endpoints
used by this project. It does not modify resources.

It expects CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID in the environment.
"""
import os
import requests
import sys


def warn(msg):
    print("WARN:", msg)


def info(msg):
    print("INFO:", msg)


def main():
    token = os.getenv("CLOUDFLARE_API_TOKEN")
    acct = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    if not token or not acct:
        print("Set CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID in env")
        return 2

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    base = "https://api.cloudflare.com/client/v4"

    tests = [
        ("List zones", f"{base}/zones"),
        ("List tunnels for account", f"{base}/accounts/{acct}/tunnels"),
    ]

    ok = True
    for name, url in tests:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            print(f"{name}: HTTP {r.status_code}")
            if r.status_code == 200:
                info(f"{name} OK")
            elif r.status_code == 403:
                warn(f"{name} returned 403 Forbidden - token likely missing needed scope")
                ok = False
            else:
                warn(f"{name} returned HTTP {r.status_code} (message: {r.text[:200]})")
                ok = False
        except Exception as e:
            warn(f"{name} failed: {e}")
            ok = False

    # Check DNS edit permission by simulating an update with an obviously-invalid id
    # We expect 403 if token lacks permission, 404 if token can access the endpoint but resource not found.
    # This is a heuristic — the API does not provide a direct "check scope" endpoint.
    sample_zone = None
    try:
        r = requests.get(f"{base}/zones", headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json().get("result", [])
            if data:
                sample_zone = data[0].get("id")
    except Exception:
        pass

    if sample_zone:
        test_url = f"{base}/zones/{sample_zone}/dns_records/00000000-0000-0000-0000-000000000000"
        try:
            r = requests.put(test_url, headers=headers, json={"type": "A"}, timeout=10)
            print(f"DNS edit test: HTTP {r.status_code}")
            if r.status_code == 403:
                warn("DNS edit endpoint returned 403 - token likely cannot edit DNS records")
                ok = False
            elif r.status_code == 404:
                info("DNS edit endpoint reachable (404 likely means resource not found). This suggests edit scope may be present.")
            else:
                info(f"DNS edit test returned HTTP {r.status_code}")
        except Exception as e:
            warn(f"DNS edit test failed: {e}")
            ok = False
    else:
        warn("Could not discover a sample zone to test DNS edit permissions")
        ok = False

    if ok:
        print("Token checks passed (heuristic). You should still use a minimal-scope token and test carefully.")
        return 0
    else:
        print("One or more checks failed. See WARN messages above for guidance.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
