This directory is intended to hold production-scraped fixtures for use in tests.

IMPORTANT: Do NOT commit API keys or any secrets. Store only sanitized JSON responses where all sensitive fields are redacted.

To fetch fixtures:
1. Use a temporarily-scoped Cloudflare API token with read-only access.
2. Run a script that calls the Cloudflare API endpoints and saves JSON output to this directory.
3. Sanitize files by removing API tokens, IPs you don't want to store, or other sensitive fields.

Example:
  python scripts/fetch_production_fixtures.py --output tests/production_fixtures
