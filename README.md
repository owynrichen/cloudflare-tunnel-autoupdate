Proxmox Cloudflare Sync
=======================

Synchronize Proxmox guest IPs with Cloudflare DNS and cloudflared tunnel routes.

Features
- Monitor multiple proxmox hosts/VMs and update Cloudflare DNS records
- Update cloudflared tunnel routes via CLI when guest IPs change
- Durable sqlite state DB
- Config via dotenv (.env)
- Extensive unit tests with network/subprocess mocking
