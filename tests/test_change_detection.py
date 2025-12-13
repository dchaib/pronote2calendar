from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from pronote2calendar.change_detection import get_changes
from pronote2calendar.event_creator import LessonEvent


def create_dummy_event(id, summary, start, end, description, location):
    return {
        "id": id,
        "summary": summary,
        "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": end.isoformat(), "timeZone": "UTC"},
        "description": description,
        "location": location,
    }


def test_get_changes_add_and_remove():
    start = datetime(2025, 10, 5, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))
    end = start + timedelta(hours=1)

    new_event = LessonEvent(
        start=start,
        end=end,
        summary="Math",
        description="Mrs. A",
        location="Room 1",
    )

    # existing event at a different time -> should be removed
    existing_event = create_dummy_event(
        "e1", "Other", start + timedelta(days=1), end + timedelta(days=1), "x", "y"
    )

    changes = get_changes([new_event], [existing_event])

    assert len(changes.to_add) == 1
    assert len(changes.to_remove) == 1
    assert len(changes.to_update) == 0
    removed = changes.to_remove[0]
    assert removed["id"] == "e1"


def test_get_changes_update_when_different():
    start = datetime(2025, 10, 5, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))
    end = start + timedelta(hours=1)

    new_event = LessonEvent(
        start=start,
        end=end,
        summary="Math",
        description="Mrs. A",
        location="Room 1",
    )

    # existing event with same start but different end and summary -> should be updated
    existing_event = create_dummy_event(
        "e2",
        "Old summary",
        start,
        end + timedelta(minutes=30),
        "Different",
        "Somewhere",
    )

    changes = get_changes([new_event], [existing_event])

    assert len(changes.to_add) == 0
    assert len(changes.to_remove) == 0
    assert len(changes.to_update) == 1
    id, updated = next(iter(changes.to_update.items()))
    assert id == "e2"
    assert updated.summary == "Math"


def test_get_changes_no_change_when_identical():
    start = datetime(2025, 10, 5, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))
    end = start + timedelta(hours=1)

    new_event = LessonEvent(
        start=start,
        end=end,
        summary="Math",
        description="Mrs. A",
        location="Room 1",
    )

    existing_event = create_dummy_event("e3", "Math", start, end, "Mrs. A", "Room 1")

    changes = get_changes([new_event], [existing_event])

    assert changes.to_add == []
    assert changes.to_remove == []
    assert changes.to_update == {}


def test_get_changes_remove_duplicate_events():
    start = datetime(2025, 10, 5, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))
    end = start + timedelta(hours=1)

    new_event = LessonEvent(
        start=start,
        end=end,
        summary="Math",
        description="Mrs. A",
        location="Room 1",
    )

    # Two existing events at the same time -> one should be removed
    existing_event1 = create_dummy_event("e4", "Math", start, end, "Mrs. A", "Room 1")
    existing_event2 = create_dummy_event("e5", "Math", start, end, "Mrs. A", "Room 1")

    changes = get_changes([new_event], [existing_event1, existing_event2])

    assert changes.to_add == []
    assert len(changes.to_remove) == 1
    assert changes.to_update == {}
    removed = changes.to_remove[0]
    assert removed["id"] in ["e4", "e5"]
