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
