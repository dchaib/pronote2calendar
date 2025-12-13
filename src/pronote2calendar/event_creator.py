import logging
from dataclasses import dataclass
from datetime import datetime

from jinja2 import Environment, StrictUndefined
from pronotepy import Lesson

from pronote2calendar.settings import EventsTemplates

logger = logging.getLogger(__name__)


@dataclass
class LessonEvent:
    start: datetime
    end: datetime
    summary: str | None
    description: str | None
    location: str | None


def build_context(lesson: Lesson) -> dict:
    return {
        "start": lesson.start,
        "end": lesson.end,
        "subject": lesson.subject.name if lesson.subject else "",
        "in_groups": lesson.subject.groups if lesson.subject else False,
        "teacher_name": lesson.teacher_name or "",
        "teacher_names": lesson.teacher_names or [],
        "classroom": lesson.classroom or "",
        "classrooms": lesson.classrooms or [],
        "virtual_classrooms": lesson.virtual_classrooms or [],
        "group_name": lesson.group_name or "",
        "group_names": lesson.group_names or [],
        "memo": lesson.memo or "",
        "status": lesson.status or "",
        "background_color": lesson.background_color or "",
        "canceled": lesson.canceled,
        "outing": lesson.outing,
        "exempted": lesson.exempted,
        "detention": lesson.detention,
        "normal": lesson.normal,
        "test": lesson.test,
    }


def render_event_fields(lesson: Lesson, templates: EventsTemplates) -> dict[str, str]:
    env = Environment(undefined=StrictUndefined)

    context = build_context(lesson)

    try:
        summary = env.from_string(templates.summary).render(context)
        description = env.from_string(templates.description).render(context)
        location = env.from_string(templates.location).render(context)
    except Exception as e:
        logger.error(
            "Error rendering templates for lesson %s: %s",
            lesson.num,
            e,
        )
        raise

    return {
        "summary": summary,
        "description": description,
        "location": location,
    }


def lesson_to_event(lesson: Lesson, templates: EventsTemplates) -> LessonEvent:
    rendered_fields = render_event_fields(lesson, templates)

    return LessonEvent(
        lesson.start,
        lesson.end,
        rendered_fields.get("summary") or None,
        rendered_fields.get("description") or None,
        rendered_fields.get("location") or None,
    )


def create_lesson_events(
    lessons: list[Lesson],
    templates: EventsTemplates,
) -> list[LessonEvent]:
    events = []
    for lesson in lessons:
        event = lesson_to_event(lesson, templates)
        events.append(event)
    return events
