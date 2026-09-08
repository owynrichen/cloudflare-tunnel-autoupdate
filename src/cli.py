from proxcloud.config import load_config
from proxcloud.cloudflare_client import CloudflareClient
from proxcloud.state import State
from proxcloud.runner import Runner
from proxcloud.mapping import load_mappings
import logging
import sys


def main(argv=None):
    logging.basicConfig(level=logging.INFO)
    cfg = load_config()
    cf = CloudflareClient(cfg.cloudflare_token, cfg.cloudflare_account)
    state = State(cfg.state_db)
    runner = Runner(cf, state)
    logging.getLogger().debug("Loaded config: %s", cfg)
    if not argv:
        argv = sys.argv[1:]
    if len(argv) < 1:
        print("Usage: cli.py <mappings.yaml>")
        return 2
    mappings = load_mappings(argv[0])
    # run dns mappings
    for m in mappings.dns:
        zid = m.zone_id or cf.get_zone_id(m.zone)
        if not zid:
            logging.error("zone id not found for %s", m.zone)
            continue
        runner.ensure_dns(zid, m.record_id, m.name, m.type, m.vm_id, lease_paths=m.lease_paths)
    # run tunnel mappings
    for t in mappings.tunnels:
        runner.ensure_tunnel_route(t.tunnel_id, t.route_id, t.vm_id, lease_paths=t.lease_paths)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
