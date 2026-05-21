from pathlib import Path

from calendar_sync.state import SyncRecord, load_state, make_state_key, save_state


def test_load_state_missing_file_returns_empty(tmp_path: Path):
    assert load_state(tmp_path / "missing.json") == {}


def test_save_and_load_state_roundtrip(tmp_path: Path):
    path = tmp_path / "state.json"
    key = make_state_key("source@example.com", "event-1")
    state = {
        key: SyncRecord(
            source_calendar_id="source@example.com",
            source_event_id="event-1",
            destination_event_id="dest-1",
            source_updated="2026-01-01T00:00:00Z",
            last_synced_at="2026-01-01T01:00:00Z",
        )
    }

    save_state(path, state)
    loaded = load_state(path)

    assert loaded[key].destination_event_id == "dest-1"
    assert loaded[key].source_updated == "2026-01-01T00:00:00Z"
