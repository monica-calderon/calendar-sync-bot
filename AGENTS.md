# AGENTS.md

## Project overview

`calendar-sync-bot` is a Python 3.12 project that synchronizes future events from one or more Google Calendar source calendars into one destination shared calendar.

## Main rules

* Never commit real credentials, tokens or `.env` files.
* Never modify source calendars.
* Never copy attendees or conference data.
* Always use `sendUpdates="none"` when creating, updating or deleting destination events.
* Keep synchronization state in `state/calendar\_sync\_state.json`.
* Preserve tests when changing sync behavior.

## Useful commands

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q

pip install -e .
python -m calendar\_sync.main
```

## Code style

* Keep Google Calendar API access in `google\_calendar.py`.
* Keep synchronization decisions in `sync.py`.
* Keep JSON state handling in `state.py`.
* Keep environment parsing in `config.py`.

