import logging
from datetime import datetime, time

from pronotepy import Lesson

from pronote2calendar.settings import TimeAdjustmentRule

logger = logging.getLogger(__name__)


def apply_time_adjustments(
    lessons: list[Lesson], adjustments_config: list[TimeAdjustmentRule]
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
    lesson: Lesson, adjustments_config: list[TimeAdjustmentRule]
) -> Lesson:
    # Get the weekday (0=Monday, 6=Sunday in Python's weekday())
    # Convert to ISO format where 1=Monday, 7=Sunday
    weekday = lesson.start.weekday() + 1

    for rule in adjustments_config:
        if weekday not in rule.weekdays:
            continue

        # Apply start time adjustment
        original_start = lesson.start.time()
        if new_start := rule.start_times.get(original_start):
            lesson.start = _apply_time_adjustment(lesson.start, new_start)
            logger.debug(
                "Adjusted start time from %s to %s for lesson at %s",
                original_start.isoformat(),
                new_start.isoformat(),
                lesson.start.isoformat(),
            )

        # Apply end time adjustment
        original_end = lesson.end.time()
        if new_end := rule.end_times.get(original_end):
            lesson.end = _apply_time_adjustment(lesson.end, new_end)
            logger.debug(
                "Adjusted end time from %s to %s for lesson at %s",
                original_end.isoformat(),
                new_end.isoformat(),
                lesson.start.isoformat(),
            )

    return lesson


def _apply_time_adjustment(dt: datetime, new_time: time) -> datetime:
    return dt.replace(hour=new_time.hour, minute=new_time.minute)
