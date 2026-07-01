from dataclasses import dataclass
import os
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    app_env: str
    backend_host: str
    backend_port: int
    frontend_host: str
    frontend_port: int
    database_path: str
    allowed_origins: tuple[str, ...]


def _int_from_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default


def get_settings() -> Settings:
    backend_host = os.getenv("BACKEND_HOST", "127.0.0.1")
    backend_port = _int_from_env("BACKEND_PORT", 8000)
    frontend_host = os.getenv("FRONTEND_HOST", "127.0.0.1")
    frontend_port = _int_from_env("FRONTEND_PORT", 5173)
    frontend_origin = f"http://{frontend_host}:{frontend_port}"

    return Settings(
        app_env=os.getenv("APP_ENV", "local"),
        backend_host=backend_host,
        backend_port=backend_port,
        frontend_host=frontend_host,
        frontend_port=frontend_port,
        database_path=os.getenv(
            "DATABASE_PATH",
            str(BACKEND_ROOT / "data" / "stock_reminder.sqlite3"),
        ),
        allowed_origins=(frontend_origin,),
    )
