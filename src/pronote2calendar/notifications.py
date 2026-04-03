import logging
from datetime import datetime, timedelta
from typing import Any, Literal, TypedDict

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


class ChangeItem(TypedDict):
    type: Literal["add", "update", "remove"]
    start: datetime
    end: datetime
    summary: str | None
    location: str | None
    description: str | None
    data: dict[str, Any]


def prepare_notification_data(
    adds: list[LessonEvent], updates: list[UpdateDiff], removes: list[CalendarEvent]
) -> dict[str, Any]:
    adds_dicts = [_event_to_dict(e) for e in adds]
    updates_dicts = [update_diff_to_dict(u) for u in updates]
    removes_dicts = [_event_to_dict(e) for e in removes]

    # Create normalized changes list
    changes: list[ChangeItem] = []
    for a in adds:
        changes.append(
            {
                "type": "add",
                "start": a.start,
                "end": a.end,
                "summary": a.summary,
                "location": a.location,
                "description": a.description,
                "data": _event_to_dict(a),
            }
        )
    for u in updates:
        changes.append(
            {
                "type": "update",
                "start": u.new.start,
                "end": u.new.end,
                "summary": u.new.summary,
                "location": u.new.location,
                "description": u.new.description,
                "data": {
                    "old": _event_to_dict(u.old),
                    "new": _event_to_dict(u.new),
                    "changes": u.changes,
                },
            }
        )
    for r in removes:
        changes.append(
            {
                "type": "remove",
                "start": r.start,
                "end": r.end,
                "summary": r.summary,
                "location": r.location,
                "description": r.description,
                "data": _event_to_dict(r),
            }
        )
    changes_sorted = sorted(changes, key=lambda x: x["start"])

    counts = {"adds": len(adds), "updates": len(updates), "removes": len(removes)}

    return {
        "adds": adds_dicts,
        "updates": updates_dicts,
        "removes": removes_dicts,
        "changes": changes_sorted,
        "counts": counts,
    }


def render_templates(
    settings: NotificationsSettings, context: dict[str, Any]
) -> tuple[str, str]:
    """Render title and body templates."""
    env = Environment(undefined=StrictUndefined)

    default_fmt = "%Y-%m-%d %H:%M"

    def format_datetime(dt: datetime, fmt: str | None = None) -> str:
        return dt.strftime(fmt or default_fmt)

    env.filters["datetime"] = format_datetime

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
    context with ``adds``, ``updates`` and ``removes`` lists (convenience lists
    for simple templates). Items in the ``adds`` and ``removes`` lists are simple
    dictionaries containing ``summary``, ``start``, ``end``, ``location`` and
    ``description``. Entries in ``updates`` are also dictionaries, but they
    additionally include ``old`` and ``new`` sub‑dictionaries and a ``changes``
    map describing which fields changed (each value is a ``(old, new)`` tuple);
    the top‑level ``summary``/``start``/``end``/ ``location``/``description`` keys
    reflect the *new* values.

    Additionally, the context includes:
    - ``changes``: a normalized list of all changes, sorted by start time. Each
      item has ``type`` ("add", "update", or "remove"), ``start``, ``summary``,
      ``end``, ``location``, ``description``, and ``data`` (the underlying event
      dict or update structure).
    - ``counts``: dict with counts of adds, updates, removes.

    A ``datetime`` Jinja2 filter is available for formatting datetimes as
    "YYYY-MM-DD HH:MM".
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
