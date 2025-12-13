import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from pronote2calendar.event_creator import LessonEvent

logger = logging.getLogger(__name__)


@dataclass
class ChangeSet:
    to_add: list[LessonEvent]
    to_update: dict[Any, LessonEvent]
    to_remove: list[dict[str, Any]]


def get_changes(
    new_events: list[LessonEvent],
    existing_events: list[dict[str, Any]],
) -> ChangeSet:
    add: list[LessonEvent] = []
    remove: list[dict[str, Any]] = []
    update: dict[Any, LessonEvent] = {}

    # Map new events to their start time
    new_events_dict = {event.start.isoformat(): event for event in new_events}

    logger.debug("Considering %d new events for changes", len(new_events_dict))

    # Map existing events to their start time,
    # allowing for multiple events at the same time
    existing_events_map = defaultdict(list)
    for event in existing_events:
        start_time = event["start"].get("dateTime", event["start"].get("date"))
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
                    event.get("end", {}).get("dateTime") == new_event.end.isoformat()
                    and event.get("summary") == new_event.summary
                    and event.get("location") == new_event.location
                    and event.get("description") == new_event.description
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
                # If no matching event is found, update the first event
                # and remove others
                update[existing_events_map[start_time][0]["id"]] = new_event
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
    for id, item_to_update in changes.to_update.items():
        logger.debug("UPDATE (id %s): %r", id, item_to_update)
    for item_to_remove in changes.to_remove:
        logger.debug("REMOVE: %r", item_to_remove)

    return changes
