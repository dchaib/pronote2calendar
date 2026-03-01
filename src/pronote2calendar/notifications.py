import logging
from datetime import datetime, timedelta
from typing import Any

from apprise import Apprise  # type: ignore
from jinja2 import Environment, StrictUndefined

from pronote2calendar.change_detection import ChangeSet
from pronote2calendar.event_creator import LessonEvent
from pronote2calendar.settings import NotificationsSettings

logger = logging.getLogger(__name__)


def _event_to_dict(event: Any) -> dict[str, Any]:
    # Accept either LessonEvent or dict from calendar
    if isinstance(event, LessonEvent):
        return {
            "summary": event.summary,
            "start": event.start,
            "end": event.end,
            "location": event.location,
            "description": event.description,
        }
    else:
        # already a dict; copy limited fields
        return {
            "summary": event.get("summary"),
            "start": event.get("start", {}).get("dateTime")
            or event.get("start", {}).get("date"),
            "end": event.get("end", {}).get("dateTime")
            or event.get("end", {}).get("date"),
            "location": event.get("location"),
            "description": event.get("description"),
        }


def _parse_start(start_value: Any) -> datetime | None:
    # start_value may be iso string or datetime
    if isinstance(start_value, datetime):
        return start_value
    if isinstance(start_value, str):
        try:
            return datetime.fromisoformat(start_value)
        except Exception:
            return None
    return None


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
    context with ``adds``, ``updates`` and ``removes`` lists; each element is a
    dict with ``summary``, ``start`` etc., so templates can access properties
    directly.
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

    def keep(ev: Any) -> bool:
        evd = _event_to_dict(ev)
        start = _parse_start(evd.get("start"))
        return start is not None and start <= limit

    adds = [_event_to_dict(e) for e in changes.to_add if keep(e)]
    updates = [_event_to_dict(e) for e in changes.to_update.values() if keep(e)]
    removes = [_event_to_dict(e) for e in changes.to_remove if keep(e)]

    if not (adds or updates or removes):
        logger.debug("All changes are beyond max_delay_days, no notification sent")
        return

    context = {
        "adds": adds,
        "updates": updates,
        "removes": removes,
        # also expose combined list if users want
        "changes": adds + updates + removes,
    }

    env = Environment(undefined=StrictUndefined)

    try:
        title = env.from_string(settings.templates.title).render(context)
        body = env.from_string(settings.templates.body).render(context)
    except Exception as e:
        logger.error("Failed to render notification templates: %s", e)
        raise

    apobj = Apprise()
    for entry in settings.destinations:
        apobj.add(entry)
    try:
        apobj.notify(title=title, body=body)
        logger.info(
            "Sent notification (%d destinations): add=%d upd=%d rem=%d",
            len(settings.destinations),
            len(adds),
            len(updates),
            len(removes),
        )
    except Exception as e:
        logger.exception("Error sending notification: %s", e)
