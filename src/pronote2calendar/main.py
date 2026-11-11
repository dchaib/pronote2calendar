import logging
from time import monotonic

from pronote2calendar import change_detection
from pronote2calendar.date_utils import compute_sync_period
from pronote2calendar.event_creator import create_lesson_events
from pronote2calendar.google_calendar_client import GoogleCalendarClient
from pronote2calendar.lesson_filters import filter_lessons
from pronote2calendar.logging_manager import setup_logging
from pronote2calendar.notifications import send_notifications
from pronote2calendar.pronote_client import PronoteClient
from pronote2calendar.settings import Settings
from pronote2calendar.subject_adjustments import apply_subject_adjustments
from pronote2calendar.time_adjustments import apply_time_adjustments

# Keep the application logger when this module is executed with python -m.
logger = logging.getLogger("pronote2calendar.main")


def main() -> int:
    started = monotonic()
    try:
        # Required fields are loaded from YAML by pydantic-settings.
        config = Settings()  # type: ignore[call-arg]
        setup_logging(config.log_level)
    except Exception as exc:
        setup_logging("ERROR", use_environment=False)
        logger.error("Error loading configuration: %s", exc)
        return 1

    try:
        start, end = compute_sync_period(config.sync.weeks)
        logger.info(
            "Synchronizing lessons from %s to %s", start.isoformat(), end.isoformat()
        )

        logger.debug("Connecting to Pronote")
        pronote = PronoteClient(
            config.pronote,
            "credentials-pronote.json",
        )
        if not pronote.is_logged_in():
            logger.error("Pronote login failed")
            return 1

        logger.debug("Fetching lessons from Pronote")
        lessons = pronote.get_lessons(start, end)
        logger.info("Fetched %d lessons from Pronote", len(lessons))
        lessons = filter_lessons(lessons, config.filters)
        lessons = apply_time_adjustments(lessons, config.adjustments.time)
        lessons = apply_subject_adjustments(lessons, config.adjustments.subject)

        logger.debug("Initializing Google Calendar client")
        calendar = GoogleCalendarClient(
            config.google_calendar, "credentials-google.json"
        )
        logger.debug("Fetching existing events from Google Calendar")
        existing_events = calendar.get_events(start, end)
        logger.info("Fetched %d existing calendar events", len(existing_events))

        new_events = create_lesson_events(lessons, config.events.templates)
        changes = change_detection.get_changes(new_events, existing_events)
        adds, updates, removes = (
            len(changes.to_add),
            len(changes.to_update),
            len(changes.to_remove),
        )
        notification_status = "skipped"
        if adds or updates or removes:
            logger.debug(
                "Applying calendar changes: add=%d update=%d remove=%d",
                adds,
                updates,
                removes,
            )
            calendar.apply_changes(changes)
            logger.info(
                "Applied calendar changes: add=%d update=%d remove=%d",
                adds,
                updates,
                removes,
            )
            result = send_notifications(config.notifications, changes)
            if result is False:
                notification_status = "failed"
            elif result is True:
                notification_status = "sent"
        else:
            logger.info("No calendar changes needed")

        logger.info(
            "Synchronization finished in %.2fs; notifications=%s",
            monotonic() - started,
            notification_status,
        )
        return 1 if notification_status == "failed" else 0
    except Exception:
        logger.exception("Synchronization failed after %.2fs", monotonic() - started)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
