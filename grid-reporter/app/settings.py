import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from .constants import DEFAULT_POLL_INTERVAL, DEFAULT_TIMEOUT


@dataclass
class Settings:
    poll_interval: int
    deye_base_url: str | None
    ext_data_url: str | None
    ext_data_token: str | None
    state_path: Path
    clients_path: Path
    timeout: int
    log_level: str
    health_port: int = 8081

    def __str__(self) -> str:
        return (
            f"Settings(poll_interval={self.poll_interval}, "
            f"deye_base_url={self.deye_base_url}, "
            f"ext_data_url={self.ext_data_url}, "
            f"state_path={self.state_path}, "
            f"clients_path={self.clients_path}, "
            f"timeout={self.timeout}, "
            f"log_level={self.log_level})"
        )


def _resolve_path(env_var: str, default: str) -> Path:
    path_str = os.getenv(env_var, default)
    path = Path(path_str)
    
    if not path.exists() and not path.is_absolute():
        parent_path = Path(__file__).parent.parent.parent / path_str
        if parent_path.exists():
            return parent_path
    
    return path


def load_settings() -> Settings:
    load_dotenv()

    s = Settings(
        poll_interval=int(
            os.getenv("POLL_INTERVAL", str(DEFAULT_POLL_INTERVAL))
        ),
        deye_base_url=os.getenv("DEYE_BASE_URL"),
        ext_data_url=os.getenv("EXT_DATA_URL"),
        ext_data_token=os.getenv("EXT_DATA_TOKEN"),
        state_path=_resolve_path("STATE_PATH", "state.json"),
        clients_path=_resolve_path("CLIENTS_PATH", "clients.json"),
        timeout=int(os.getenv("HTTP_TIMEOUT", str(DEFAULT_TIMEOUT))),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        health_port=int(os.getenv("HEALTH_PORT", "8081")),
    )
    logging.debug("Loaded settings: %s", s)
    return s
