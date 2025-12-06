import logging
from dataclasses import dataclass
from datetime import datetime

from pronotepy import Lesson

logger = logging.getLogger(__name__)


@dataclass
class LessonEvent:
    start: datetime
    end: datetime
    summary: str
    description: str | None
    location: str | None


def lesson_to_event(lesson: Lesson) -> LessonEvent:
    return LessonEvent(
        start=lesson.start,
        end=lesson.end,
        summary=lesson.subject.name if lesson.subject is not None else "",
        location=lesson.classroom,
        description=lesson.teacher_name,
    )


def create_lesson_events(
    lessons: list[Lesson],
) -> list[LessonEvent]:
    events = []
    for lesson in lessons:
        event = lesson_to_event(lesson)
        events.append(event)
    return events
