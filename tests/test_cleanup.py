from pathlib import Path

from calendar_sync.config import Config
from calendar_sync.cleanup import delete_all_synced_events
from calendar_sync.state import SyncRecord, make_state_key


class FakeService:
    pass


def test_cleanup_deletes_state_events_and_clears_state(monkeypatch):
    deleted = []

    def fake_list_synced_events(service, destination_calendar_id):
        return [{"id": "dest-from-tag"}]

    def fake_delete(service, destination_calendar_id, destination_event_id):
        deleted.append((destination_calendar_id, destination_event_id))

    monkeypatch.setattr("calendar_sync.cleanup.list_synced_destination_events", fake_list_synced_events)
    monkeypatch.setattr("calendar_sync.cleanup.delete_destination_event", fake_delete)

    key = make_state_key("source@example.com", "event-1")
    state = {
        key: SyncRecord(
            source_calendar_id="source@example.com",
            source_event_id="event-1",
            destination_event_id="dest-from-state",
            source_updated="2026-05-20T10:00:00Z",
            last_synced_at="2026-05-20T11:00:00Z",
        )
    }

    result = delete_all_synced_events(FakeService(), "dest@example.com", state)

    assert result["deleted"] == 2
    assert state == {}
    assert ("dest@example.com", "dest-from-state") in deleted
    assert ("dest@example.com", "dest-from-tag") in deleted
