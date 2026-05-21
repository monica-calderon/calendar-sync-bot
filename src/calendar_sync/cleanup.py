from __future__ import annotations

import logging
import sys

from calendar_sync.config import load_config
from calendar_sync.google_calendar import build_calendar_service, delete_destination_event, list_synced_destination_events
from calendar_sync.state import load_state, save_state

LOGGER = logging.getLogger(__name__)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def delete_all_synced_events(service, destination_calendar_id: str, state) -> dict[str, int]:
    """Delete only destination events known to have been created by this bot."""
    counters = {"deleted": 0, "already_missing": 0, "errors": 0}
    destination_ids = {record.destination_event_id for record in state.values()}

    try:
        tagged_events = list_synced_destination_events(service, destination_calendar_id)
        destination_ids.update(event["id"] for event in tagged_events if event.get("id"))
    except Exception:
        LOGGER.warning("Could not list tagged destination events. Falling back to state file only.", exc_info=True)

    LOGGER.info("Found %s synced destination events to delete", len(destination_ids))

    for destination_event_id in sorted(destination_ids):
        try:
            delete_destination_event(service, destination_calendar_id, destination_event_id)
            counters["deleted"] += 1
            LOGGER.info("Deleted synced destination event: %s", destination_event_id)
        except Exception as exc:
            if getattr(getattr(exc, "resp", None), "status", None) == 404:
                counters["already_missing"] += 1
                LOGGER.warning("Synced destination event already missing: %s", destination_event_id)
            else:
                counters["errors"] += 1
                LOGGER.exception("Error deleting synced destination event: %s", destination_event_id)

    state.clear()
    LOGGER.info("Cleanup summary: %s", counters)
    return counters


def main() -> int:
    configure_logging()
    logger = logging.getLogger(__name__)

    try:
        config = load_config()
        state = load_state(config.state_file)
        service = build_calendar_service(config)
        counters = delete_all_synced_events(service, config.destination_calendar_id, state)
        save_state(config.state_file, state)
        logger.info("State cleared and saved to %s", config.state_file)
        return 1 if counters.get("errors") else 0
    except Exception:
        logger.exception("Fatal error cleaning synced calendar events")
        return 1


if __name__ == "__main__":
    sys.exit(main())
