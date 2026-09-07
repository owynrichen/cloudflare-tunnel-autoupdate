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
    proxmox_api_token: str | None = os.getenv("PROXMOX_API_TOKEN")


def load_config() -> Config:
    token = os.getenv("CLOUDFLARE_API_TOKEN")
    acct = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    if not token or not acct:
        raise RuntimeError("CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID must be set in env")
    return Config(cloudflare_token=token, cloudflare_account=acct)
