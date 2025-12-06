import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import pronotepy

logger = logging.getLogger(__name__)


@dataclass
class ChangeSet:
    to_add: list[dict[str, Any]]
    to_update: dict[Any, dict[str, Any]]
    to_remove: list[dict[str, Any]]


def lesson_to_event(lesson: pronotepy.Lesson) -> dict[str, Any]:
    return {
        "start": lesson.start,
        "end": lesson.end,
        "summary": lesson.subject.name if lesson.subject is not None else "",
        "location": lesson.classroom,
        "description": lesson.teacher_name,
    }


def get_changes(
    lessons: list[pronotepy.Lesson], events: list[dict[str, Any]]
) -> ChangeSet:
    add: list[dict[str, Any]] = []
    remove: list[dict[str, Any]] = []
    update: dict[Any, dict[str, Any]] = {}

    # Map lessons to their start time (timezone-aware)
    lesson_events = {
        lesson.start.isoformat(): lesson_to_event(lesson) for lesson in lessons
    }
    logger.debug("Considering %d lessons for changes", len(lesson_events))

    # Map events to their start time, allowing for multiple events at the same time
    event_map = defaultdict(list)
    for event in events:
        start_time = event["start"].get("dateTime", event["start"].get("date"))
        event_map[start_time].append(event)

    logger.debug(
        "Considering %d existing events from calendar for changes",
        sum(len(v) for v in event_map.values()),
    )

    # Check lessons to add or update
    for start_time, lesson_event in lesson_events.items():
        if start_time not in event_map:
            add.append(lesson_event)
        else:
            matching_events = [
                event
                for event in event_map[start_time]
                if (
                    event.get("end", {}).get("dateTime")
                    == lesson_event["end"].isoformat()
                    and event.get("summary") == lesson_event["summary"]
                    and event.get("location") == lesson_event.get("location")
                    and event.get("description") == lesson_event["description"]
                )
            ]

            if matching_events:
                # Remove all other matching events
                remove.extend(matching_events[1:])
                # Remove non-matching events
                remove.extend(
                    [
                        event
                        for event in event_map[start_time]
                        if event not in matching_events
                    ]
                )
            else:
                # If no matching event is found, update the first event
                # and remove others
                update[event_map[start_time][0]["id"]] = lesson_event
                remove.extend(event_map[start_time][1:])

    # Check events to remove that don't have a matching lesson
    for start_time, event_list in event_map.items():
        if start_time not in lesson_events:
            remove.extend(event_list)

    logger.debug(
        "Change detection results: add=%d remove=%d update=%d",
        len(add),
        len(remove),
        len(update),
    )
    changes = ChangeSet(add, update, remove)

    for item in changes.to_add:
        logger.debug("ADD: %r", item)
    for id, item in changes.to_update.items():
        logger.debug("UPDATE (id %s): %r", id, item)
    for item in changes.to_remove:
        logger.debug("REMOVE: %r", item)

    return changes
