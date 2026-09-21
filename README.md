Proxmox Cloudflare Sync
=======================

Synchronize Proxmox guest IPs with Cloudflare DNS and cloudflared tunnel routes.

Features
- Monitor multiple proxmox hosts/VMs and update Cloudflare DNS records
- Update cloudflared tunnel routes via API when guest IPs change
- Durable sqlite state DB
- Config via dotenv (.env)
- Extensive unit tests with network/subprocess mocking

Agent Usage
- All commands should be run with `uv` per AGENTS.md

Notes / Next Steps
- mappings.generated.yaml is currently empty when exported from Cloudflare for this account. You should:
  1. Inspect `examples/mappings.generated.yaml` and fill `vm_id` values for tunnels you want to manage.
  2. If some tunnels are missing from the export, check Cloudflare API permissions for the token used by this tool.

- Security: the local development `.env` is configured to disable TLS verification for the Proxmox API (PROXMOX_API_VERIFY=false). For production set PROXMOX_API_VERIFY=true and use a hostname that matches the Proxmox TLS certificate.

- Scheduling: we added `scripts/check_tunnels.py` (dry-run by default) and `scripts/scan_macs.py`. To run on a schedule, create a systemd timer that calls `uv run -- python scripts/check_tunnels.py /path/to/mappings.yaml` or use your preferred scheduler.

- Workflow:
  1. Export mappings from Cloudflare: `python -m src.proxcloud.tunnel_mapper` (or use the provided functions) to create `examples/mappings.generated.yaml`.
  2. Edit that file to set `vm_id` for each tunnel route you wish to track.
  3. Run a dry-run to see planned updates: `python scripts/check_tunnels.py examples/mappings.generated.yaml --node pve`.
  4. If output looks correct, run with `--apply` to commit changes to Cloudflare and persist state.

Additional Improvements (future):
- Automatic vm_id assignment heuristics (match hostnames / MACs to tunnel endpoints).
- Robust logging (rotating file logs, structured JSON output).
- Add systemd timer unit and example service wrapper for deployment.
