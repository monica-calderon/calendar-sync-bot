from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class SyncRecord:
    source_calendar_id: str
    source_event_id: str
    destination_event_id: str
    source_updated: str | None
    last_synced_at: str

    @property
    def key(self) -> str:
        return make_state_key(self.source_calendar_id, self.source_event_id)


def make_state_key(source_calendar_id: str, source_event_id: str) -> str:
    return f"{source_calendar_id}::{source_event_id}"


def load_state(path: Path) -> dict[str, SyncRecord]:
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as file:
        raw = json.load(file)

    records = raw.get("records", raw if isinstance(raw, dict) else {})
    state: dict[str, SyncRecord] = {}
    for key, value in records.items():
        state[key] = SyncRecord(**value)
    return state


def save_state(path: Path, state: dict[str, SyncRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "records": {key: asdict(record) for key, record in sorted(state.items())}
    }
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2, sort_keys=True)
        file.write("\n")
