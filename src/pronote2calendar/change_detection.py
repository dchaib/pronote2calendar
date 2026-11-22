import logging
from collections import defaultdict

from pronote2calendar.models import CalendarEvent, ChangeSet, LessonEvent, UpdateDiff

logger = logging.getLogger(__name__)


def _build_update(existing: CalendarEvent, desired: LessonEvent) -> UpdateDiff:
    fields = {
        "summary": (existing.summary, desired.summary),
        "end": (existing.end.isoformat(), desired.end.isoformat()),
        "location": (existing.location, desired.location),
        "description": (existing.description, desired.description),
    }
    return UpdateDiff(
        id=existing.id,
        old=existing,
        new=desired,
        changes={
            name: values for name, values in fields.items() if values[0] != values[1]
        },
    )


def get_changes(
    new_events: list[LessonEvent],
    existing_events: list[CalendarEvent],
) -> ChangeSet:
    add: list[LessonEvent] = []
    remove: list[CalendarEvent] = []
    update: list[UpdateDiff] = []

    new_events_map: defaultdict[str, list[LessonEvent]] = defaultdict(list)
    for new_event in new_events:
        new_events_map[new_event.start.isoformat()].append(new_event)

    logger.debug("Considering %d new events for changes", len(new_events))

    existing_events_map: defaultdict[str, list[CalendarEvent]] = defaultdict(list)
    for event in existing_events:
        start_time = event.start.isoformat()
        existing_events_map[start_time].append(event)

    logger.debug(
        "Considering %d existing events from calendar for changes",
        len(existing_events),
    )

    for start_time, desired_events in new_events_map.items():
        remaining_existing = existing_events_map.pop(start_time, [])
        remaining_desired: list[LessonEvent] = []

        # Keep events that already match a lesson. Each event can match once.
        for desired in desired_events:
            for index, existing in enumerate(remaining_existing):
                if (
                    existing.end == desired.end
                    and existing.summary == desired.summary
                    and existing.location == desired.location
                    and existing.description == desired.description
                ):
                    remaining_existing.pop(index)
                    break
            else:
                remaining_desired.append(desired)

        # Update the remaining pairs at this start time, then handle the surplus.
        pair_count = min(len(remaining_desired), len(remaining_existing))
        for index in range(pair_count):
            update.append(
                _build_update(remaining_existing[index], remaining_desired[index])
            )
        add.extend(remaining_desired[pair_count:])
        remove.extend(remaining_existing[pair_count:])

    for event_list in existing_events_map.values():
        remove.extend(event_list)

    logger.debug(
        "Change detection results: add=%d update=%d remove=%d",
        len(add),
        len(update),
        len(remove),
    )
    changes = ChangeSet(add, update, remove)

    for item_to_add in changes.to_add:
        logger.debug("ADD: %r", item_to_add)
    for item_to_update in changes.to_update:
        logger.debug("UPDATE (id %s): %r", item_to_update.id, item_to_update)
    for item_to_remove in changes.to_remove:
        logger.debug("REMOVE: %r", item_to_remove)

    return changes
