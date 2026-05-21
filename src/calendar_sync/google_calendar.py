from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from calendar_sync.config import Config

SCOPES = ["https://www.googleapis.com/auth/calendar"]
TOKEN_URI = "https://oauth2.googleapis.com/token"


def build_calendar_service(config: Config):
    # Imported lazily so unit tests for pure sync/state logic do not require Google packages.
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    credentials = Credentials(
        token=None,
        refresh_token=config.google_refresh_token,
        token_uri=TOKEN_URI,
        client_id=config.google_client_id,
        client_secret=config.google_client_secret,
        scopes=SCOPES,
    )
    return build("calendar", "v3", credentials=credentials, cache_discovery=False)


def utc_window(days_ahead: int) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=days_ahead)
    return now.isoformat().replace("+00:00", "Z"), end.isoformat().replace("+00:00", "Z")


def get_calendar_name(service, calendar_id: str) -> str:
    """Return the human-readable calendar name, falling back to its id."""
    calendar = service.calendars().get(calendarId=calendar_id).execute()
    return calendar.get("summary") or calendar_id


def list_source_events(service, calendar_id: str, days_ahead: int) -> list[dict[str, Any]]:
    time_min, time_max = utc_window(days_ahead)
    events: list[dict[str, Any]] = []
    page_token = None

    while True:
        response = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime",
                showDeleted=True,
                pageToken=page_token,
            )
            .execute()
        )
        events.extend(response.get("items", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return events


def list_synced_destination_events(service, destination_calendar_id: str) -> list[dict[str, Any]]:
    """List destination events tagged as created by this bot."""
    events: list[dict[str, Any]] = []
    page_token = None

    while True:
        response = (
            service.events()
            .list(
                calendarId=destination_calendar_id,
                privateExtendedProperty="calendarSyncBot=true",
                showDeleted=False,
                pageToken=page_token,
            )
            .execute()
        )
        events.extend(response.get("items", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return events


def create_destination_event(service, destination_calendar_id: str, event_body: dict[str, Any]) -> dict[str, Any]:
    return (
        service.events()
        .insert(calendarId=destination_calendar_id, body=event_body, sendUpdates="none")
        .execute()
    )


def update_destination_event(
    service, destination_calendar_id: str, destination_event_id: str, event_body: dict[str, Any]
) -> dict[str, Any]:
    return (
        service.events()
        .patch(
            calendarId=destination_calendar_id,
            eventId=destination_event_id,
            body=event_body,
            sendUpdates="none",
        )
        .execute()
    )


def delete_destination_event(service, destination_calendar_id: str, destination_event_id: str) -> None:
    service.events().delete(
        calendarId=destination_calendar_id,
        eventId=destination_event_id,
        sendUpdates="none",
    ).execute()
