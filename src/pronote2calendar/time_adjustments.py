import logging
from datetime import datetime
from typing import Any

from pronotepy import Lesson

logger = logging.getLogger(__name__)


def apply_time_adjustments(
    lessons: list[Lesson], adjustments_config: list[dict[str, Any]] | None
) -> list[Lesson]:
    if not adjustments_config:
        logger.debug("No time adjustments configured")
        return lessons

    logger.debug("Applying time adjustments to %d lessons", len(lessons))

    adjusted_lessons = []
    for lesson in lessons:
        adjusted_lesson = _adjust_lesson_time(lesson, adjustments_config)
        adjusted_lessons.append(adjusted_lesson)

    return adjusted_lessons


def _adjust_lesson_time(
    lesson: Lesson, adjustments_config: list[dict[str, Any]]
) -> Lesson:
    # Get the weekday (0=Monday, 6=Sunday in Python's weekday())
    # Convert to ISO format where 1=Monday, 7=Sunday
    weekday = lesson.start.weekday() + 1

    for rule in adjustments_config:
        weekdays = rule.get("weekdays", [])

        if weekday not in weekdays:
            continue

        # Apply start time adjustment
        start_times_map = rule.get("start_times", {})
        if start_times_map:
            current_start_str = lesson.start.strftime("%H:%M")
            if current_start_str in start_times_map:
                new_start_str = start_times_map[current_start_str]
                lesson.start = _apply_time_adjustment(lesson.start, new_start_str)
                logger.debug(
                    "Adjusted start time from %s to %s for lesson at %s",
                    current_start_str,
                    new_start_str,
                    lesson.start.isoformat(),
                )

        # Apply end time adjustment
        end_times_map = rule.get("end_times", {})
        if end_times_map:
            current_end_str = lesson.end.strftime("%H:%M")
            if current_end_str in end_times_map:
                new_end_str = end_times_map[current_end_str]
                lesson.end = _apply_time_adjustment(lesson.end, new_end_str)
                logger.debug(
                    "Adjusted end time from %s to %s for lesson at %s",
                    current_end_str,
                    new_end_str,
                    lesson.end.isoformat(),
                )

    return lesson


def _apply_time_adjustment(dt: datetime, new_time_str: str) -> datetime:
    parts = new_time_str.split(":")
    hours = int(parts[0])
    minutes = int(parts[1]) if len(parts) > 1 else 0

    return dt.replace(hour=hours, minute=minutes)
