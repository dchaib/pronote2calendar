from datetime import datetime, timedelta
import pytest

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


def test_select_highest_num_per_start():
    now = datetime.now()
    lessons = [
        DummyLesson(now, 1),
        DummyLesson(now, 2),
        DummyLesson(now + timedelta(hours=1), 1),
    ]

    pc = PronoteClient.__new__(PronoteClient)
    result = pc.sort_and_filter_lessons(lessons)

    # For the same start time, the lesson with num=2 should be chosen
    assert any(l.num == 2 for l in result)
    # total lessons should be 2 (one for each start time)
    assert len(result) == 2


def test_select_highest_num_per_start_even_if_canceled():
    now = datetime.now()
    lessons = [DummyLesson(now, 1), DummyLesson(now, 2, canceled=True)]

    pc = PronoteClient.__new__(PronoteClient)
    result = pc.sort_and_filter_lessons(lessons)

    # total lessons should be 0 because the highest num lesson is canceled
    assert len(result) == 0
