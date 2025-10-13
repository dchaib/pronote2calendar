from datetime import date, datetime, timedelta
from pronote2calendar import change_detection
from pronote2calendar.config_manager import read_config
from pronote2calendar.pronote_client import PronoteClient
from pronote2calendar.google_calendar_client import GoogleCalendarClient
import logging
from pronote2calendar.logging_manager import setup_logging


def main():
    config = read_config()

    setup_logging(config.get("log_level"))

    logger = logging.getLogger("pronote2calendar")

    start = datetime.combine(date.today(), datetime.min.time()).astimezone()
    end = start + timedelta(days=config["max_days"])

    logger.info("Updating lessons from %s to %s", start.isoformat(), end.isoformat())

    try:
        logger.info("Initializing Pronote client")
        pronote = PronoteClient(config["pronote"], "credentials-pronote.json")

        if not pronote.is_logged_in():
            logger.error("Pronote login failed")
            return

        logger.info("Fetching lessons from Pronote")
        lessons = pronote.get_lessons(start, end)
        logger.info("Fetched %d lessons", len(lessons) if lessons is not None else 0)

        logger.info("Initializing Google Calendar client")
        calendar = GoogleCalendarClient(
            config["google_calendar"], "credentials-google.json"
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
