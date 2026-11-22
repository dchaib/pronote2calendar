from datetime import datetime, timedelta

from pronote2calendar.pronote_client import PronoteClient


class DummyLesson:
    def __init__(self, start, num, canceled=False):
        self.start = start
        self.num = num
        self.canceled = canceled


def test_skip_canceled_lessons():
    now = datetime.now()
    lessons = [
        DummyLesson(now, 1, canceled=True),
        DummyLesson(now + timedelta(minutes=30), 1),
    ]

    pc = PronoteClient.__new__(PronoteClient)
    result = pc.sort_and_filter_lessons(lessons)

    # canceled lesson should be skipped, only one remains
    assert len(result) == 1
    assert result[0].start == lessons[1].start


def test_keep_active_lessons_with_same_start():
    now = datetime.now()
    lessons = [
        DummyLesson(now + timedelta(hours=1), 1),
        DummyLesson(now, 2),
        DummyLesson(now, 1),
    ]

    pc = PronoteClient.__new__(PronoteClient)
    result = pc.sort_and_filter_lessons(lessons)

    assert result == [lessons[1], lessons[2], lessons[0]]


def test_keep_room_change_when_canceled_lesson_has_higher_num():
    now = datetime.now()
    replacement = DummyLesson(now, 1286)
    lessons = [DummyLesson(now, 1365, canceled=True), replacement]

    pc = PronoteClient.__new__(PronoteClient)
    result = pc.sort_and_filter_lessons(lessons)

    assert result == [replacement]
