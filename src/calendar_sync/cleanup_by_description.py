from __future__ import annotations

import logging

from calendar_sync.config import load_config
from calendar_sync.google_calendar import build_calendar_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)


def delete_events_with_description_text():
    config = load_config()
    service = build_calendar_service(config)

    calendar_id = config.destination_calendar_id

    # Texto a buscar dentro de la descripción
    search_text = "[Synced from calendar-sync-bot]"

    page_token = None
    deleted_count = 0

    logger.info("Searching events in calendar: %s", calendar_id)

    while True:
        response = (
            service.events()
            .list(
                calendarId=calendar_id,
                maxResults=2500,
                singleEvents=True,
                showDeleted=False,
                pageToken=page_token,
            )
            .execute()
        )

        events = response.get("items", [])

        for event in events:
            description = event.get("description", "")

            if search_text.lower() in description.lower():
                event_id = event["id"]
                summary = event.get("summary", "(No title)")

                logger.info(
                    "Deleting event | %s | %s",
                    summary,
                    event_id,
                )

                (
                    service.events()
                    .delete(
                        calendarId=calendar_id,
                        eventId=event_id,
                        sendUpdates="none",
                    )
                    .execute()
                )

                deleted_count += 1

        page_token = response.get("nextPageToken")

        if not page_token:
            break

    logger.info("Finished. Deleted events: %s", deleted_count)


if __name__ == "__main__":
    delete_events_with_description_text()