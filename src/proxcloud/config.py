from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()


@dataclass
class Config:
    cloudflare_token: str
    cloudflare_account: str
    state_db: str = os.getenv("STATE_DB", "state.db")
    proxmox_api_url: str | None = os.getenv("PROXMOX_API_URL")
    # PROXMOX_API_TOKEN may be the raw token value. If the token id (user@realm!id)
    # is supplied separately, the client will combine them into a single header value.
    proxmox_api_token: str | None = os.getenv("PROXMOX_API_TOKEN")
    proxmox_api_token_id: str | None = os.getenv("PROXMOX_API_TOKEN_ID")
    proxmox_api_verify: bool = os.getenv("PROXMOX_API_VERIFY", "true").lower() not in ("0", "false", "no")


def load_config() -> Config:
    token = os.getenv("CLOUDFLARE_API_TOKEN")
    acct = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    if not token or not acct:
        raise RuntimeError("CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID must be set in env")
    return Config(cloudflare_token=token, cloudflare_account=acct)
