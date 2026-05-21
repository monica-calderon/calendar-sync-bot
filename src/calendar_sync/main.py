from __future__ import annotations

import logging
import sys

from calendar_sync.config import load_config
from calendar_sync.google_calendar import build_calendar_service
from calendar_sync.state import load_state, save_state
from calendar_sync.sync import run_sync


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def main() -> int:
    configure_logging()
    logger = logging.getLogger(__name__)

    try:
        config = load_config()
        logger.info("Loading state from %s", config.state_file)
        state = load_state(config.state_file)
        service = build_calendar_service(config)
        counters = run_sync(service, config, state)
        save_state(config.state_file, state)
        logger.info("State saved to %s", config.state_file)
        return 1 if counters.get("errors") else 0
    except Exception:
        logger.exception("Fatal error running calendar sync")
        return 1


if __name__ == "__main__":
    sys.exit(main())
