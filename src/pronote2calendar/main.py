import logging

from pronote2calendar import change_detection
from pronote2calendar.date_utils import compute_sync_period
from pronote2calendar.google_calendar_client import GoogleCalendarClient
from pronote2calendar.logging_manager import setup_logging
from pronote2calendar.pronote_client import PronoteClient
from pronote2calendar.settings import Settings
from pronote2calendar.time_adjustments import apply_time_adjustments


def main():
    try:
        config = Settings()
    except Exception as e:
        setup_logging("ERROR")
        logger = logging.getLogger("pronote2calendar")
        logger.error("Error loading configuration: %s", e)
        return

    setup_logging(config.log_level)

    logger = logging.getLogger("pronote2calendar")

    start, end = compute_sync_period(config.sync.weeks)

    logger.info("Updating lessons from %s to %s", start.isoformat(), end.isoformat())

    try:
        logger.info("Initializing Pronote client")
        pronote = PronoteClient(config.pronote, "credentials-pronote.json")

        if not pronote.is_logged_in():
            logger.error("Pronote login failed")
            return

        logger.info("Fetching lessons from Pronote")
        lessons = pronote.get_lessons(start, end)
        logger.info("Fetched %d lessons", len(lessons) if lessons is not None else 0)

        logger.info("Applying time adjustments to lessons")
        lessons = apply_time_adjustments(lessons, config.time_adjustments)

        logger.info("Initializing Google Calendar client")
        calendar = GoogleCalendarClient(
            config.google_calendar, "credentials-google.json"
        )
        logger.info("Fetching events from Google Calendar")
        events = calendar.get_events(start, end)
        logger.info(
            "Fetched %d existing events", len(events) if events is not None else 0
        )

        logger.info("Detecting changes between lessons and calendar events")
        changes = change_detection.get_changes(lessons, events)
        adds = len(changes.get("add", []))
        removes = len(changes.get("remove", []))
        updates = len(changes.get("update", []))
        logger.info(
            "Change detection produced add=%d remove=%d update=%d",
            adds,
            removes,
            updates,
        )

        if adds == 0 and removes == 0 and updates == 0:
            logger.info("No changes to apply, skipping calendar update")
        else:
            logger.info("Applying changes to calendar")
            calendar.apply_changes(changes)
            logger.info("Finished applying changes")

    except Exception as exc:
        logger.exception("Unhandled exception in main: %s", exc)
        raise


if __name__ == "__main__":
    main()
