"""Sanitize JSON fixtures by redacting sensitive values.

Usage:
  python scripts/sanitize_fixtures.py --input tests/production_fixtures --output tests/production_fixtures_sanitized

This will copy JSON files from input to output, recursively replacing:
- any value that looks like an IPv4 address with the string "REDACTED_IP"
- any value for keys containing "token", "authorization", "api_key", "secret", or "password" with "REDACTED"

Be careful: review output before committing.
"""
import argparse
import json
import os
import re
from typing import Any


IPV4_RE = re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b")

SENSITIVE_KEYS = ["token", "authorization", "api_key", "apiKey", "secret", "password", "private_key"]


def sanitize_value(key: str, value: Any) -> Any:
    # If key name suggests secret, redact entirely
    if isinstance(key, str) and any(k.lower() in key.lower() for k in SENSITIVE_KEYS):
        return "REDACTED"

    # If string contains IPv4 address, redact IPs
    if isinstance(value, str):
        if IPV4_RE.search(value):
            # replace all ip-like patterns
            return IPV4_RE.sub("REDACTED_IP", value)
        return value

    return value


def sanitize(obj: Any) -> Any:
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            out[k] = sanitize_value(k, sanitize(v))
        return out
    elif isinstance(obj, list):
        return [sanitize(x) for x in obj]
    else:
        return sanitize_value("", obj)


def process_file(inpath: str, outpath: str):
    with open(inpath, "r") as f:
        try:
            data = json.load(f)
        except Exception:
            # if file not json, copy raw
            with open(outpath, "wb") as out:
                out.write(open(inpath, "rb").read())
            return
    s = sanitize(data)
    with open(outpath, "w") as f:
        json.dump(s, f, indent=2)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()

    os.makedirs(args.output, exist_ok=True)
    for root, dirs, files in os.walk(args.input):
        rel = os.path.relpath(root, args.input)
        outdir = os.path.join(args.output, rel) if rel != "." else args.output
        os.makedirs(outdir, exist_ok=True)
        for fn in files:
            if not fn.lower().endswith(".json"):
                continue
            inpath = os.path.join(root, fn)
            outpath = os.path.join(outdir, fn)
            print(f"Sanitizing {inpath} -> {outpath}")
            process_file(inpath, outpath)


if __name__ == "__main__":
    main()
