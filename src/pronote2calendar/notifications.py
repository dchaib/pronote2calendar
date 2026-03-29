import logging
from datetime import datetime, timedelta
from typing import Any

from apprise import Apprise  # type: ignore
from jinja2 import Environment, StrictUndefined

from pronote2calendar.models import CalendarEvent, ChangeSet, LessonEvent, UpdateDiff
from pronote2calendar.settings import NotificationsSettings

logger = logging.getLogger(__name__)


def _event_to_dict(event: LessonEvent | CalendarEvent) -> dict[str, Any]:
    """Convert an Event to a dict suitable for templates."""
    return {
        "summary": event.summary,
        "start": event.start,
        "end": event.end,
        "location": event.location,
        "description": event.description,
    }


def update_diff_to_dict(update: UpdateDiff) -> dict[str, Any]:
    """Convert an UpdateDiff into a dictionary suitable for templates.

    The resulting dict contains ``id``, ``old`` (a simple dict), ``new`` and
    ``changes`` (mapping field -> (old, new)).  ``new`` is similar to
    ``old`` but derived from the Event.
    """

    result: dict[str, Any] = {
        "id": update.id,
        "start": update.new.start,
        "old": _event_to_dict(update.old),
        "new": _event_to_dict(update.new),
        "changes": update.changes,
    }
    return result


def filter_changes_by_date(
    changes: ChangeSet, limit: datetime
) -> tuple[list[LessonEvent], list[UpdateDiff], list[CalendarEvent]]:
    """Filter changes to only include those with start <= limit."""

    adds = [e for e in changes.to_add if e.start <= limit]
    updates = [
        u for u in changes.to_update if (u.new.start <= limit or u.old.start <= limit)
    ]
    removes = [e for e in changes.to_remove if e.start <= limit]
    return adds, updates, removes


def prepare_notification_data(
    adds: list[LessonEvent], updates: list[UpdateDiff], removes: list[CalendarEvent]
) -> dict[str, Any]:
    """Prepare the data for template rendering."""
    adds_dicts = [_event_to_dict(e) for e in adds]
    updates_dicts = [update_diff_to_dict(u) for u in updates]
    removes_dicts = [_event_to_dict(e) for e in removes]

    # Combine all changes into a single sorted list
    all_changes = adds_dicts + updates_dicts + removes_dicts
    all_changes_sorted = sorted(all_changes, key=lambda x: x["start"])

    return {
        "adds": adds_dicts,
        "updates": updates_dicts,
        "removes": removes_dicts,
        "changes": all_changes_sorted,
    }


def render_templates(
    settings: NotificationsSettings, context: dict[str, Any]
) -> tuple[str, str]:
    """Render title and body templates."""
    env = Environment(undefined=StrictUndefined)

    try:
        title = env.from_string(settings.templates.title).render(context)
        body = env.from_string(settings.templates.body).render(context)
    except Exception as e:
        logger.error("Failed to render notification templates: %s", e)
        raise

    return title, body


def send_via_apprise(destinations: list[str], title: str, body: str) -> None:
    """Send notification via Apprise."""
    apobj = Apprise()
    for entry in destinations:
        apobj.add(entry)
    try:
        apobj.notify(title=title, body=body)
        logger.info(
            "Sent notification (%d destinations)",
            len(destinations),
        )
    except Exception as e:
        logger.exception("Error sending notification: %s", e)


def send_notifications(
    settings: NotificationsSettings, changes: ChangeSet, now: datetime | None = None
) -> None:
    """Send a single notification via Apprise summarizing the provided changes.

    If ``settings.enabled`` is False the function returns immediately.  The
    ``settings.destinations`` list may contain multiple service URLs or paths
    to Apprise-compatible configuration files; each entry is passed to
    ``Apprise.add()``.  An empty list results in a no-op.

    The ``max_delay_days`` value is used to discard any change whose start time
    is more than that many days in the future relative to ``now`` (which is
    ``datetime.now().astimezone()`` if not supplied).  All three change types
    (adds, updates, removes) are filtered.

    The templates defined in ``settings.templates`` are rendered using a
    context with ``adds``, ``updates`` and ``removes`` lists.  Items in the
    ``adds`` and ``removes`` lists are simple dictionaries containing
    ``summary``, ``start``, ``end``, ``location`` and ``description``.  Entries
    in ``updates`` are also dictionaries, but they additionally include
    ``old`` and ``new`` sub‑dictionaries and a ``changes`` map describing which
    fields changed (each value is a ``(old, new)`` tuple); for backward
    compatibility the top‑level ``summary``/``start``/``end``/``location``/
    ``description`` keys reflect the *new* values.
    """

    if not settings.enabled:
        logger.debug("Notifications disabled in configuration, skipping")
        return

    if not settings.destinations:
        logger.debug("No notification destinations configured, skipping")
        return

    if not (changes.to_add or changes.to_update or changes.to_remove):
        logger.debug("No changes detected, skipping notification")
        return

    now = now or datetime.now().astimezone()
    limit = now + timedelta(days=settings.max_delay_days)

    adds, updates, removes = filter_changes_by_date(changes, limit)

    if not (adds or updates or removes):
        logger.debug("All changes are beyond max_delay_days, no notification sent")
        return

    context = prepare_notification_data(adds, updates, removes)

    title, body = render_templates(settings, context)

    logger.info("Prepared notification with title: %s and body:\n%s", title, body)

    send_via_apprise(settings.destinations, title, body)
