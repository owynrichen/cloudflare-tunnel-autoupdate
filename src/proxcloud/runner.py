import logging
from .state import State
from .cloudflare_client import CloudflareClient
from . import proxmox

logger = logging.getLogger(__name__)


class Runner:
    def __init__(self, cf: CloudflareClient, state: State):
        self.cf = cf
        self.state = state

    def ensure_dns(self, zone_id: str, record_id: str, name: str, type_: str, vm_id: str, lease_paths: list | None = None):
        ip = proxmox.get_guest_ip(vm_id, lease_paths)
        if not ip:
            logger.warning("no ip for vm %s", vm_id)
            return False
        prev = self.state.get(record_id)
        if prev == ip:
            logger.debug("ip unchanged for %s", name)
            return True
        # update cloudflare
        self.cf.update_dns(zone_id, record_id, name, type_, ip)
        self.state.set(record_id, ip)
        logger.info("updated %s -> %s", name, ip)
        return True

    def ensure_tunnel_route(self, tunnel_id: str, route_id: str, vm_id: str, lease_paths: list | None = None):
        """Ensure a tunnel route points to the vm's current IP.
        route_id is the Cloudflare route id (persisted as state key).
        """
        ip = proxmox.get_guest_ip(vm_id, lease_paths)
        if not ip:
            logger.warning("no ip for vm %s", vm_id)
            return False
        prev = self.state.get(route_id)
        if prev == ip:
            logger.debug("tunnel route unchanged for %s", route_id)
            return True

        # update via Cloudflare Tunnels API
        dest = f"ip:{ip}"
        self.cf.update_tunnel_route(tunnel_id, route_id, dest)
        self.state.set(route_id, ip)
        logger.info("updated tunnel %s route %s -> %s", tunnel_id, route_id, ip)
        return True
