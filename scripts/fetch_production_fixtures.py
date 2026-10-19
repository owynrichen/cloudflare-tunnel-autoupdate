"""Fetch Cloudflare API data for building sanitized test fixtures.

This script should be run locally by a human with a token in their env.
It will save JSON responses into the target directory. It will NOT commit them.
"""
import os
from dotenv import load_dotenv
import requests
import json
import argparse

load_dotenv()


def save(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="tests/production_fixtures")
    args = parser.parse_args()

    token = os.getenv("CLOUDFLARE_API_TOKEN")
    acct = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    if not token or not acct:
        raise SystemExit("set CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID in env")

    headers = {"Authorization": f"Bearer {token}"}
    base = "https://api.cloudflare.com/client/v4"

    os.makedirs(args.output, exist_ok=True)

    # zones
    r = requests.get(f"{base}/zones", headers=headers)
    r.raise_for_status()
    save(os.path.join(args.output, "zones.json"), r.json())

    # example: list dns records for each zone
    for z in r.json().get("result", []):
        zid = z.get("id")
        rr = requests.get(f"{base}/zones/{zid}/dns_records", headers=headers)
        rr.raise_for_status()
        save(os.path.join(args.output, f"dns_{zid}.json"), rr.json())

    # tunnels for account
    tr = requests.get(f"{base}/accounts/{acct}/tunnels", headers=headers)
    tr.raise_for_status()
    save(os.path.join(args.output, "tunnels.json"), tr.json())

    # fetch routes for each tunnel and save
    for t in tr.json().get("result", []):
        tid = t.get("id")
        if not tid:
            continue
        rr = requests.get(f"{base}/accounts/{acct}/tunnels/{tid}/routes", headers=headers)
        # don't fail the whole run if routes endpoint is not allowed
        if rr.status_code == 404:
            print(f"warning: routes not available for tunnel {tid} (403/404)")
            continue
        rr.raise_for_status()
        save(os.path.join(args.output, f"routes_{tid}.json"), rr.json())

    print("Wrote fixtures to", args.output)


if __name__ == "__main__":
    main()
