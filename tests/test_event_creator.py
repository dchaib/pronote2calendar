from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from pronote2calendar.event_creator import lesson_to_event


class DummyLesson:
    def __init__(self, start, end, subject_name, classroom, teacher_name):
        class Subject:
            def __init__(self, name):
                self.name = name

        self.start = start
        self.end = end
        self.subject = Subject(subject_name)
        self.classroom = classroom
        self.teacher_name = teacher_name
        self.num = 1


def test_lesson_to_event_mapping():
    start = datetime(2025, 10, 5, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))
    end = start + timedelta(hours=1)
    lesson = DummyLesson(start, end, "Math", "Room 1", "Mrs. A")

    ev = lesson_to_event(lesson)

    assert ev.start == start
    assert ev.end == end
    assert ev.summary == "Math"
    assert ev.location == "Room 1"
    assert ev.description == "Mrs. A"
