from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from pronote2calendar.change_detection import lesson_to_event, get_changes


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


def create_dummy_event(id, summary, start, end, description, location):
    return {
        "id": id,
        "summary": summary,
        "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": end.isoformat(), "timeZone": "UTC"},
        "description": description,
        "location": location,
    }


def test_lesson_to_event_mapping():
    start = datetime(2025, 10, 5, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))
    end = start + timedelta(hours=1)
    lesson = DummyLesson(start, end, "Math", "Room 1", "Mrs. A")

    ev = lesson_to_event(lesson)

    assert ev["start"] == start
    assert ev["end"] == end
    assert ev["summary"] == "Math"
    assert ev["location"] == "Room 1"
    assert ev["description"] == "Mrs. A"


def test_get_changes_add_and_remove():
    start = datetime(2025, 10, 5, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))
    end = start + timedelta(hours=1)
    lesson = DummyLesson(start, end, "Math", "Room 1", "Mrs. A")

    # existing event at a different time -> should be removed
    existing_event = create_dummy_event(
        "e1", "Other", start + timedelta(days=1), end + timedelta(days=1), "x", "y"
    )

    changes = get_changes([lesson], [existing_event])

    assert len(changes["add"]) == 1
    assert len(changes["remove"]) == 1
    assert len(changes["update"]) == 0
    removed = changes["remove"][0]
    assert removed["id"] == "e1"


def test_get_changes_update_when_different():
    start = datetime(2025, 10, 5, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))
    end = start + timedelta(hours=1)
    lesson = DummyLesson(start, end, "Math", "Room 1", "Mrs. A")

    # existing event with same start but different end and summary -> should be updated
    existing_event = create_dummy_event(
        "e2",
        "Old summary",
        start,
        end + timedelta(minutes=30),
        "Different",
        "Somewhere",
    )

    changes = get_changes([lesson], [existing_event])

    assert len(changes["add"]) == 0
    assert len(changes["remove"]) == 0
    assert len(changes["update"]) == 1
    updated = changes["update"][0]
    assert updated["id"] == "e2"
    assert updated["summary"] == "Math"


def test_get_changes_no_change_when_identical():
    start = datetime(2025, 10, 5, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))
    end = start + timedelta(hours=1)
    lesson = DummyLesson(start, end, "Math", "Room 1", "Mrs. A")
    existing_event = create_dummy_event("e3", "Math", start, end, "Mrs. A", "Room 1")

    changes = get_changes([lesson], [existing_event])

    assert changes["add"] == []
    assert changes["remove"] == []
    assert changes["update"] == []


def test_get_changes_remove_duplicate_events():
    start = datetime(2025, 10, 5, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))
    end = start + timedelta(hours=1)
    lesson = DummyLesson(start, end, "Math", "Room 1", "Mrs. A")

    # Two existing events at the same time -> one should be removed
    existing_event1 = create_dummy_event("e4", "Math", start, end, "Mrs. A", "Room 1")
    existing_event2 = create_dummy_event("e5", "Math", start, end, "Mrs. A", "Room 1")

    changes = get_changes([lesson], [existing_event1, existing_event2])

    assert changes["add"] == []
    assert len(changes["remove"]) == 1
    assert changes["update"] == []
    removed = changes["remove"][0]
    assert removed["id"] in ["e4", "e5"]
