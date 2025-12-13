from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from jinja2 import TemplateError

from pronote2calendar.event_creator import (
    create_lesson_events,
    lesson_to_event,
    render_event_fields,
)
from pronote2calendar.settings import EventsTemplates


class DummySubject:
    def __init__(self, name, groups=False):
        self.name = name
        self.groups = groups


class DummyLesson:
    def __init__(
        self,
        start,
        end,
        subject_name=None,
        classroom=None,
        teacher_name=None,
        num=1,
    ):
        self.start = start
        self.end = end
        self.subject = DummySubject(subject_name) if subject_name else None
        self.classroom = classroom
        self.teacher_name = teacher_name
        self.num = num
        self.teacher_names = [teacher_name] if teacher_name else []
        self.classrooms = [classroom] if classroom else []
        self.canceled = False
        self.status = None
        self.background_color = None
        self.outing = False
        self.memo = None
        self.group_name = None
        self.group_names = []
        self.exempted = False
        self.virtual_classrooms = []
        self.detention = False
        self.normal = True
        self.test = False


def test_lesson_to_event_mapping():
    """Test basic lesson to event mapping with default templates."""
    start = datetime(2025, 10, 5, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))
    end = start + timedelta(hours=1)
    lesson = DummyLesson(start, end, "Math", "Room 1", "Mrs. A")

    templates = EventsTemplates()
    ev = lesson_to_event(lesson, templates)

    assert ev.start == start
    assert ev.end == end
    assert ev.summary == "Math"
    assert ev.location == "Room 1"
    assert ev.description == "Mrs. A"


def test_lesson_to_event_with_none_values():
    """Test event creation when lesson has None values."""
    start = datetime(2025, 10, 5, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))
    end = start + timedelta(hours=1)
    lesson = DummyLesson(
        start,
        end,
        subject_name="English",
        classroom=None,
        teacher_name=None,
    )

    templates = EventsTemplates()
    ev = lesson_to_event(lesson, templates)

    assert ev.start == start
    assert ev.end == end
    assert ev.summary == "English"
    assert ev.location is None
    assert ev.description is None


def test_custom_template_summary_only():
    """Test template with custom summary."""
    start = datetime(2025, 10, 5, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))
    end = start + timedelta(hours=1)
    lesson = DummyLesson(start, end, "Physics", "Lab 2", "Dr. Smith")

    templates = EventsTemplates(
        summary="LESSON: {{ subject }}",
        description="",
        location="",
    )
    ev = lesson_to_event(lesson, templates)

    assert ev.summary == "LESSON: Physics"
    assert ev.description is None
    assert ev.location is None


def test_custom_template_with_multiple_fields():
    """Test template combining multiple lesson fields."""
    start = datetime(2025, 10, 5, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))
    end = start + timedelta(hours=1)
    lesson = DummyLesson(start, end, "Chemistry", "Lab 3", "Prof. Johnson")

    templates = EventsTemplates(
        summary="{{ subject }} with {{ teacher_name }}",
        description="Location: {{ classroom }}",
        location="{{ classroom }}",
    )
    ev = lesson_to_event(lesson, templates)

    assert ev.summary == "Chemistry with Prof. Johnson"
    assert ev.description == "Location: Lab 3"
    assert ev.location == "Lab 3"


def test_template_with_conditional():
    """Test template with conditional logic."""
    start = datetime(2025, 10, 5, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))
    end = start + timedelta(hours=1)
    lesson = DummyLesson(start, end, "History", "Room 5", "Mrs. Brown")

    templates = EventsTemplates(
        summary="{{ subject if subject else 'No Subject' }}",
        description="{{ teacher_name or 'Unknown Teacher' }}",
        location="{{ classroom or 'TBA' }}",
    )
    ev = lesson_to_event(lesson, templates)

    assert ev.summary == "History"
    assert ev.description == "Mrs. Brown"
    assert ev.location == "Room 5"


def test_template_with_conditional_for_missing_subject():
    """Test conditional template when subject is None."""
    start = datetime(2025, 10, 5, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))
    end = start + timedelta(hours=1)
    lesson = DummyLesson(
        start,
        end,
        subject_name=None,
        classroom="Room 6",
        teacher_name="Mr. White",
    )

    templates = EventsTemplates(
        summary="{{ subject if subject else 'No Subject' }}",
        description="{{ teacher_name or 'Unknown Teacher' }}",
        location="{{ classroom or 'TBA' }}",
    )
    ev = lesson_to_event(lesson, templates)

    assert ev.summary == "No Subject"
    assert ev.description == "Mr. White"
    assert ev.location == "Room 6"


def test_template_with_fallback_for_none_fields():
    """Test fallback values in template when fields are None."""
    start = datetime(2025, 10, 5, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))
    end = start + timedelta(hours=1)
    lesson = DummyLesson(
        start,
        end,
        subject_name="Biology",
        classroom=None,
        teacher_name=None,
    )

    templates = EventsTemplates(
        summary="{{ subject if subject else 'Unknown' }}",
        description="{{ teacher_name or 'No teacher' }}",
        location="{{ classroom or 'Room TBA' }}",
    )
    ev = lesson_to_event(lesson, templates)

    assert ev.summary == "Biology"
    assert ev.description == "No teacher"
    assert ev.location == "Room TBA"


def test_template_with_undefined_variable_strict_mode():
    """Test that undefined variables in strict mode raise an error."""
    start = datetime(2025, 10, 5, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))
    end = start + timedelta(hours=1)
    lesson = DummyLesson(start, end, "Math", "Room 1", "Mrs. A")

    # Template using an undefined variable that doesn't exist on lesson object
    templates = EventsTemplates(
        summary="{{ lesson.undefined_field }}",
        description="",
        location="",
    )

    with pytest.raises(TemplateError):
        lesson_to_event(lesson, templates)


def test_template_with_invalid_syntax():
    """Test that invalid Jinja2 syntax raises an error."""
    start = datetime(2025, 10, 5, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))
    end = start + timedelta(hours=1)
    lesson = DummyLesson(start, end, "Math", "Room 1", "Mrs. A")

    # Invalid Jinja2 syntax
    templates = EventsTemplates(
        summary="{{ lesson.subject.name }",  # Missing closing brace
        description="",
        location="",
    )

    with pytest.raises(TemplateError):
        lesson_to_event(lesson, templates)


def test_render_event_fields_error_propagation():
    """Test that render_event_fields properly propagates template errors."""
    lesson = DummyLesson(
        datetime(2025, 10, 5, 9, 0, tzinfo=ZoneInfo("Europe/Paris")),
        datetime(2025, 10, 5, 10, 0, tzinfo=ZoneInfo("Europe/Paris")),
        "Math",
        "Room 1",
        "Mrs. A",
    )

    templates = EventsTemplates(
        summary="{{ nonexistent }}",
        description="",
        location="",
    )

    with pytest.raises(TemplateError) as exc_info:
        render_event_fields(lesson, templates)

    # Verify error contains useful information
    error_str = str(exc_info.value).lower()
    assert "error" in error_str or "nonexistent" in error_str


def test_create_lesson_events_with_default_templates():
    """Test creating multiple events with default templates."""
    start = datetime(2025, 10, 5, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))
    lessons = [
        DummyLesson(
            start,
            start + timedelta(hours=1),
            "Math",
            "Room 1",
            "Mrs. A",
            num=1,
        ),
        DummyLesson(
            start + timedelta(hours=2),
            start + timedelta(hours=3),
            "English",
            "Room 2",
            "Mr. B",
            num=2,
        ),
        DummyLesson(
            start + timedelta(hours=4),
            start + timedelta(hours=5),
            "Science",
            "Lab",
            "Dr. C",
            num=3,
        ),
    ]

    templates = EventsTemplates()
    events = create_lesson_events(lessons, templates)

    assert len(events) == 3
    assert events[0].summary == "Math"
    assert events[1].summary == "English"
    assert events[2].summary == "Science"


def test_create_lesson_events_with_custom_template():
    """Test creating multiple events with custom template."""
    start = datetime(2025, 10, 5, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))
    lessons = [
        DummyLesson(
            start,
            start + timedelta(hours=1),
            "Math",
            "Room 1",
            "Mrs. A",
            num=1,
        ),
        DummyLesson(
            start + timedelta(hours=2),
            start + timedelta(hours=3),
            "English",
            "Room 2",
            "Mr. B",
            num=2,
        ),
    ]

    templates = EventsTemplates(
        summary="[{{ classroom }}] {{ subject }}",
        description="{{ teacher_name }}",
        location="{{ classroom }}",
    )
    events = create_lesson_events(lessons, templates)

    assert len(events) == 2
    assert events[0].summary == "[Room 1] Math"
    assert events[0].description == "Mrs. A"
    assert events[1].summary == "[Room 2] English"
    assert events[1].description == "Mr. B"


def test_create_lesson_events_empty_list():
    """Test creating events from an empty lesson list."""
    templates = EventsTemplates()
    events = create_lesson_events([], templates)

    assert len(events) == 0
    assert events == []


def test_create_lesson_events_with_one_invalid_template():
    """Test that error in one lesson's template stops processing."""
    start = datetime(2025, 10, 5, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))
    lessons = [
        DummyLesson(
            start,
            start + timedelta(hours=1),
            "Math",
            "Room 1",
            "Mrs. A",
            num=1,
        ),
        DummyLesson(
            start + timedelta(hours=2),
            start + timedelta(hours=3),
            "English",
            "Room 2",
            "Mr. B",
            num=2,
        ),
    ]

    # Template with undefined variable
    templates = EventsTemplates(
        summary="{{ lesson.undefined_field }}",
        description="",
        location="",
    )

    with pytest.raises(TemplateError):
        create_lesson_events(lessons, templates)


def test_template_with_empty_strings():
    """Test template that results in empty strings."""
    start = datetime(2025, 10, 5, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))
    end = start + timedelta(hours=1)
    lesson = DummyLesson(start, end, "Math", "Room 1", "Mrs. A")

    templates = EventsTemplates(
        summary="",
        description="",
        location="",
    )
    ev = lesson_to_event(lesson, templates)

    assert ev.summary is None
    assert ev.description is None
    assert ev.location is None
