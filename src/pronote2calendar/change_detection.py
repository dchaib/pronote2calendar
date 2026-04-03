import logging
from collections import defaultdict

from pronote2calendar.models import CalendarEvent, ChangeSet, LessonEvent, UpdateDiff

logger = logging.getLogger(__name__)


def get_changes(
    new_events: list[LessonEvent],
    existing_events: list[CalendarEvent],
) -> ChangeSet:
    add: list[LessonEvent] = []
    remove: list[CalendarEvent] = []
    update: list[UpdateDiff] = []

    # Map new events to their start time
    new_events_dict = {event.start.isoformat(): event for event in new_events}

    logger.debug("Considering %d new events for changes", len(new_events_dict))

    # Map existing events to their start time,
    # allowing for multiple events at the same time
    existing_events_map: defaultdict[str, list[CalendarEvent]] = defaultdict(list)
    for event in existing_events:
        start_time = event.start.isoformat()
        existing_events_map[start_time].append(event)

    logger.debug(
        "Considering %d existing events from calendar for changes",
        sum(len(v) for v in existing_events_map.values()),
    )

    # Check new events to add or update
    for start_time, new_event in new_events_dict.items():
        if start_time not in existing_events_map:
            add.append(new_event)
        else:
            matching_events = [
                event
                for event in existing_events_map[start_time]
                if (
                    event.end == new_event.end
                    and event.summary == new_event.summary
                    and event.location == new_event.location
                    and event.description == new_event.description
                )
            ]

            if matching_events:
                # Remove all other matching events
                remove.extend(matching_events[1:])
                # Remove non-matching events
                remove.extend(
                    [
                        event
                        for event in existing_events_map[start_time]
                        if event not in matching_events
                    ]
                )
            else:
                # If no matching event is found, build a diff object for
                # the first existing event and record it as an update.
                old_event = existing_events_map[start_time][0]

                changes_map = {
                    "summary": (old_event.summary, new_event.summary),
                    "start": (old_event.start.isoformat(), new_event.start.isoformat()),
                    "end": (old_event.end.isoformat(), new_event.end.isoformat()),
                    "location": (old_event.location, new_event.location),
                    "description": (old_event.description, new_event.description),
                }
                # Only include changed fields
                changes_map = {k: v for k, v in changes_map.items() if v[0] != v[1]}

                update.append(
                    UpdateDiff(
                        id=old_event.id,
                        old=old_event,
                        new=new_event,
                        changes=changes_map,
                    )
                )
                # still remove any duplicates
                remove.extend(existing_events_map[start_time][1:])

    # Check events to remove that don't have a matching new event
    for start_time, event_list in existing_events_map.items():
        if start_time not in new_events_dict:
            remove.extend(event_list)

    logger.debug(
        "Change detection results: add=%d remove=%d update=%d",
        len(add),
        len(remove),
        len(update),
    )
    changes = ChangeSet(add, update, remove)

    for item_to_add in changes.to_add:
        logger.debug("ADD: %r", item_to_add)
    for item_to_update in changes.to_update:
        logger.debug("UPDATE (id %s): %r", item_to_update.id, item_to_update)
    for item_to_remove in changes.to_remove:
        logger.debug("REMOVE: %r", item_to_remove)

    return changes
