from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    google_client_id: str
    google_client_secret: str
    google_refresh_token: str
    source_calendar_ids: list[str]
    destination_calendar_id: str
    days_ahead: int = 90
    timezone: str = "UTC"
    state_file: Path = Path("state/calendar_sync_state.json")
    event_owner_name: str = "Mónica"


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise ValueError(f"Missing required environment variable: {name}")
    return value.strip()


def load_config(env_file: str | None = None) -> Config:
    """Load configuration from environment variables and optional .env file."""
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()

    raw_sources = _required_env("SOURCE_CALENDAR_IDS")
    source_calendar_ids = [item.strip() for item in raw_sources.split(",") if item.strip()]
    if not source_calendar_ids:
        raise ValueError("SOURCE_CALENDAR_IDS must contain at least one calendar id")

    try:
        days_ahead = int(os.getenv("DAYS_AHEAD", "90"))
    except ValueError as exc:
        raise ValueError("DAYS_AHEAD must be an integer") from exc

    if days_ahead <= 0:
        raise ValueError("DAYS_AHEAD must be greater than 0")

    return Config(
        google_client_id=_required_env("GOOGLE_CLIENT_ID"),
        google_client_secret=_required_env("GOOGLE_CLIENT_SECRET"),
        google_refresh_token=_required_env("GOOGLE_REFRESH_TOKEN"),
        source_calendar_ids=source_calendar_ids,
        destination_calendar_id=_required_env("DESTINATION_CALENDAR_ID"),
        days_ahead=days_ahead,
        timezone=os.getenv("TIMEZONE", "UTC").strip() or "UTC",
        state_file=Path(os.getenv("STATE_FILE", "state/calendar_sync_state.json")),
        event_owner_name=os.getenv("EVENT_OWNER_NAME", "Mónica").strip() or "Mónica",
    )
