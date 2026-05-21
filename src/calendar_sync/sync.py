from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from calendar_sync.config import Config
from calendar_sync.google_calendar import (
    create_destination_event,
    delete_destination_event,
    get_calendar_name,
    list_source_events,
    update_destination_event,
)
from calendar_sync.state import SyncRecord, make_state_key

LOGGER = logging.getLogger(__name__)
SYNC_MARKER = "[Synced from calendar-sync-bot]"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def clean_old_sync_metadata(description: str) -> str:
    """Remove the old technical footer if it exists in a previously synced event."""
    if SYNC_MARKER not in description:
        return description.strip()
    return description.split(SYNC_MARKER, 1)[0].strip()


def build_description(source_event: dict[str, Any], source_calendar_name: str, owner_name: str) -> str:
    original = clean_old_sync_metadata(source_event.get("description", "") or "")
    friendly_marker = f"Evento de {owner_name} - {source_calendar_name}"
    if original:
        return f"{original}\n\n{friendly_marker}".strip()
    return friendly_marker


def build_extended_properties(source_event: dict[str, Any], source_calendar_id: str) -> dict[str, Any]:
    return {
        "private": {
            "calendarSyncBot": "true",
            "sourceCalendarId": source_calendar_id,
            "sourceEventId": source_event.get("id", ""),
        }
    }


def build_destination_event_body(
    source_event: dict[str, Any],
    source_calendar_id: str,
    timezone_name: str,
    source_calendar_name: str | None = None,
    owner_name: str = "Mónica",
) -> dict[str, Any]:
    display_calendar_name = source_calendar_name or source_calendar_id
    body: dict[str, Any] = {
        "summary": source_event.get("summary", "Sin título"),
        "description": build_description(source_event, display_calendar_name, owner_name),
        "start": dict(source_event["start"]),
        "end": dict(source_event["end"]),
        "visibility": source_event.get("visibility", "default"),
        "transparency": source_event.get("transparency", "opaque"),
        "reminders": {"useDefault": True},
        "extendedProperties": build_extended_properties(source_event, source_calendar_id),
    }

    if source_event.get("location"):
        body["location"] = source_event["location"]

    if "dateTime" in body["start"] and "timeZone" not in body["start"]:
        body["start"]["timeZone"] = timezone_name
    if "dateTime" in body["end"] and "timeZone" not in body["end"]:
        body["end"]["timeZone"] = timezone_name

    # Deliberately do not copy attendees, conferenceData or custom reminders.
    return body


def event_has_changed(source_event: dict[str, Any], record: SyncRecord) -> bool:
    return source_event.get("updated") != record.source_updated


def sync_source_event(
    service,
    config: Config,
    source_calendar_id: str,
    source_event: dict[str, Any],
    state: dict[str, SyncRecord],
    source_calendar_name: str | None = None,
) -> str:
    source_event_id = source_event["id"]
    key = make_state_key(source_calendar_id, source_event_id)
    record = state.get(key)
    status = source_event.get("status")

    if status == "cancelled":
        if record:
            try:
                delete_destination_event(service, config.destination_calendar_id, record.destination_event_id)
                LOGGER.info("Deleted destination event for cancelled source event: %s", key)
            except Exception as exc:
                if getattr(getattr(exc, "resp", None), "status", None) == 404:
                    LOGGER.warning("Destination event already missing for cancelled source event: %s", key)
                else:
                    raise
            del state[key]
            return "cancelled"
        LOGGER.info("Skipped cancelled source event without existing copy: %s", key)
        return "skipped_cancelled"

    body = build_destination_event_body(
        source_event,
        source_calendar_id,
        config.timezone,
        source_calendar_name=source_calendar_name,
        owner_name=config.event_owner_name,
    )

    if record is None:
        created = create_destination_event(service, config.destination_calendar_id, body)
        state[key] = SyncRecord(
            source_calendar_id=source_calendar_id,
            source_event_id=source_event_id,
            destination_event_id=created["id"],
            source_updated=source_event.get("updated"),
            last_synced_at=now_iso(),
        )
        LOGGER.info("Created destination event: %s -> %s", key, created["id"])
        return "created"

    if event_has_changed(source_event, record):
        update_destination_event(service, config.destination_calendar_id, record.destination_event_id, body)
        record.source_updated = source_event.get("updated")
        record.last_synced_at = now_iso()
        state[key] = record
        LOGGER.info("Updated destination event: %s -> %s", key, record.destination_event_id)
        return "updated"

    LOGGER.info("Skipped unchanged event: %s", key)
    return "skipped"


def run_sync(service, config: Config, state: dict[str, SyncRecord]) -> dict[str, int]:
    counters = {
        "created": 0,
        "updated": 0,
        "cancelled": 0,
        "skipped": 0,
        "skipped_cancelled": 0,
        "errors": 0,
    }

    for source_calendar_id in config.source_calendar_ids:
        LOGGER.info("Reading source calendar: %s", source_calendar_id)
        try:
            source_calendar_name = get_calendar_name(service, source_calendar_id)
        except Exception:
            source_calendar_name = source_calendar_id
            LOGGER.warning("Could not read calendar name. Falling back to calendar id: %s", source_calendar_id)

        events = list_source_events(service, source_calendar_id, config.days_ahead)
        LOGGER.info("Found %s source events in %s", len(events), source_calendar_id)

        for event in events:
            try:
                result = sync_source_event(service, config, source_calendar_id, event, state, source_calendar_name)
                counters[result] = counters.get(result, 0) + 1
            except Exception:
                counters["errors"] += 1
                LOGGER.exception(
                    "Error syncing event %s from calendar %s",
                    event.get("id", "<without-id>"),
                    source_calendar_id,
                )

    LOGGER.info("Sync summary: %s", counters)
    return counters
