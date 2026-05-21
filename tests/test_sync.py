from dataclasses import replace
from pathlib import Path

import pytest

from calendar_sync.config import Config
from calendar_sync.state import SyncRecord, make_state_key
from calendar_sync.sync import build_destination_event_body, sync_source_event


class FakeService:
    pass


@pytest.fixture
def config(tmp_path: Path):
    return Config(
        google_client_id="client-id",
        google_client_secret="client-secret",
        google_refresh_token="refresh-token",
        source_calendar_ids=["source@example.com"],
        destination_calendar_id="dest@example.com",
        days_ahead=60,
        timezone="Europe/Madrid",
        state_file=tmp_path / "state.json",
        event_owner_name="Mónica",
    )


@pytest.fixture
def source_event():
    return {
        "id": "event-1",
        "status": "confirmed",
        "summary": "Demo event",
        "description": "Original description",
        "start": {"dateTime": "2026-06-01T10:00:00+02:00"},
        "end": {"dateTime": "2026-06-01T11:00:00+02:00"},
        "updated": "2026-05-20T10:00:00Z",
        "attendees": [{"email": "person@example.com"}],
        "conferenceData": {"dummy": True},
    }


def test_destination_body_does_not_copy_attendees_or_conference(source_event):
    body = build_destination_event_body(source_event, "source@example.com", "Europe/Madrid", "Trabajo", "Mónica")

    assert body["summary"] == "Demo event"
    assert "attendees" not in body
    assert "conferenceData" not in body
    assert body["description"].endswith("Evento de Mónica - Trabajo")
    assert "[Synced from calendar-sync-bot]" not in body["description"]
    assert body["extendedProperties"]["private"]["calendarSyncBot"] == "true"
    assert body["reminders"] == {"useDefault": True}


def test_new_event_is_created(monkeypatch, config, source_event):
    created_payloads = []

    def fake_create(service, destination_calendar_id, event_body):
        created_payloads.append((destination_calendar_id, event_body))
        return {"id": "dest-event-1"}

    monkeypatch.setattr("calendar_sync.sync.create_destination_event", fake_create)

    state = {}
    result = sync_source_event(FakeService(), config, "source@example.com", source_event, state)

    key = make_state_key("source@example.com", "event-1")
    assert result == "created"
    assert state[key].destination_event_id == "dest-event-1"
    assert created_payloads[0][0] == "dest@example.com"


def test_updated_event_is_updated(monkeypatch, config, source_event):
    updated_payloads = []

    def fake_update(service, destination_calendar_id, destination_event_id, event_body):
        updated_payloads.append((destination_calendar_id, destination_event_id, event_body))
        return {"id": destination_event_id}

    monkeypatch.setattr("calendar_sync.sync.update_destination_event", fake_update)

    key = make_state_key("source@example.com", "event-1")
    state = {
        key: SyncRecord(
            source_calendar_id="source@example.com",
            source_event_id="event-1",
            destination_event_id="dest-event-1",
            source_updated="old-update",
            last_synced_at="2026-05-19T10:00:00Z",
        )
    }

    result = sync_source_event(FakeService(), config, "source@example.com", source_event, state)

    assert result == "updated"
    assert state[key].source_updated == "2026-05-20T10:00:00Z"
    assert updated_payloads[0][1] == "dest-event-1"


def test_unchanged_event_is_skipped(monkeypatch, config, source_event):
    def fail_update(*args, **kwargs):
        raise AssertionError("Update should not be called")

    monkeypatch.setattr("calendar_sync.sync.update_destination_event", fail_update)

    key = make_state_key("source@example.com", "event-1")
    state = {
        key: SyncRecord(
            source_calendar_id="source@example.com",
            source_event_id="event-1",
            destination_event_id="dest-event-1",
            source_updated="2026-05-20T10:00:00Z",
            last_synced_at="2026-05-20T11:00:00Z",
        )
    }

    result = sync_source_event(FakeService(), config, "source@example.com", source_event, state)

    assert result == "skipped"


def test_cancelled_event_deletes_destination(monkeypatch, config, source_event):
    deleted = []

    def fake_delete(service, destination_calendar_id, destination_event_id):
        deleted.append((destination_calendar_id, destination_event_id))

    monkeypatch.setattr("calendar_sync.sync.delete_destination_event", fake_delete)

    cancelled_event = dict(source_event)
    cancelled_event["status"] = "cancelled"

    key = make_state_key("source@example.com", "event-1")
    state = {
        key: SyncRecord(
            source_calendar_id="source@example.com",
            source_event_id="event-1",
            destination_event_id="dest-event-1",
            source_updated="2026-05-20T10:00:00Z",
            last_synced_at="2026-05-20T11:00:00Z",
        )
    }

    result = sync_source_event(FakeService(), config, "source@example.com", cancelled_event, state)

    assert result == "cancelled"
    assert key not in state
    assert deleted == [("dest@example.com", "dest-event-1")]


def test_existing_old_marker_is_removed_from_description(source_event):
    source_event = dict(source_event)
    source_event["description"] = "Texto original\n\n[Synced from calendar-sync-bot]\nSource calendar: old\nSource event: old"

    body = build_destination_event_body(source_event, "source@example.com", "Europe/Madrid", "Personal", "Mónica")

    assert body["description"] == "Texto original\n\nEvento de Mónica - Personal"
