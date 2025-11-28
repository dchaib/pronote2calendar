from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from pronote2calendar.settings import TimeAdjustment
from pronote2calendar.time_adjustments import apply_time_adjustments


class DummyLesson:
    """Mock lesson object for testing"""

    def __init__(self, start: datetime, end: datetime, subject_name: str = "Math"):
        class Subject:
            def __init__(self, name):
                self.name = name

        self.start = start
        self.end = end
        self.subject = Subject(subject_name)
        self.classroom = "Room 1"
        self.teacher_name = "Teacher"
        self.num = 1


def test_no_adjustments_returns_unchanged():
    """When no adjustments are configured, lessons should be unchanged"""
    start = datetime(2025, 10, 6, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))  # Monday
    end = start + timedelta(hours=1)
    lesson = DummyLesson(start, end)

    result = apply_time_adjustments([lesson], None)

    assert len(result) == 1
    assert result[0].start == start
    assert result[0].end == end


def test_empty_adjustments_list_returns_unchanged():
    """When adjustments list is empty, lessons should be unchanged"""
    start = datetime(2025, 10, 6, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))  # Monday
    end = start + timedelta(hours=1)
    lesson = DummyLesson(start, end)

    result = apply_time_adjustments([lesson], [])

    assert len(result) == 1
    assert result[0].start == start
    assert result[0].end == end


def test_adjust_start_time_with_list_of_weekdays():
    """Adjust start time when weekday matches a list of weekdays"""
    start = datetime(2025, 10, 6, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))  # Monday
    end = start + timedelta(hours=1)
    lesson = DummyLesson(start, end)

    adjustments = [
        TimeAdjustment(
            weekdays=[1, 2, 4, 5],  # Monday, Tuesday, Thursday, Friday
            start_times={time(9, 0): time(8, 55)},
        )
    ]

    result = apply_time_adjustments([lesson], adjustments)

    assert result[0].start.strftime("%H:%M") == "08:55"
    assert result[0].end == end


def test_adjust_end_time_with_list_of_weekdays():
    """Adjust end time when weekday matches a list of weekdays"""
    start = datetime(2025, 10, 6, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))  # Monday
    end = start + timedelta(hours=1)
    end = end.replace(hour=10)  # 10:00
    lesson = DummyLesson(start, end)

    adjustments = [
        TimeAdjustment(
            weekdays=[1, 2, 4, 5],
            end_times={time(10, 0): time(10, 5)},
        )
    ]

    result = apply_time_adjustments([lesson], adjustments)

    assert result[0].start == start
    assert result[0].end.strftime("%H:%M") == "10:05"


def test_adjust_both_start_and_end_times():
    """Adjust both start and end times in same rule"""
    start = datetime(2025, 10, 6, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))  # Monday
    end = start + timedelta(hours=1)
    end = end.replace(hour=10)  # 10:00
    lesson = DummyLesson(start, end)

    adjustments = [
        TimeAdjustment(
            weekdays=[1, 2, 4, 5],
            start_times={time(9, 0): time(8, 55)},
            end_times={time(10, 0): time(10, 5)},
        )
    ]

    result = apply_time_adjustments([lesson], adjustments)

    assert result[0].start.strftime("%H:%M") == "08:55"
    assert result[0].end.strftime("%H:%M") == "10:05"


def test_no_adjustment_when_weekday_does_not_match():
    """No adjustment when weekday doesn't match the rule"""
    start = datetime(2025, 10, 5, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))  # Sunday
    end = start + timedelta(hours=1)
    lesson = DummyLesson(start, end)

    adjustments = [
        TimeAdjustment(
            weekdays=[1, 2, 3, 4, 5],  # Monday-Friday
            start_times={time(9, 0): time(8, 55)},
        )
    ]

    result = apply_time_adjustments([lesson], adjustments)

    assert result[0].start == start
    assert result[0].end == end


def test_no_adjustment_when_time_does_not_match():
    """No adjustment when the time doesn't match any rule"""
    start = datetime(2025, 10, 6, 10, 30, tzinfo=ZoneInfo("Europe/Paris"))  # Monday
    end = start + timedelta(hours=1)
    lesson = DummyLesson(start, end)

    adjustments = [
        TimeAdjustment(
            weekdays=[1, 2, 4, 5],
            start_times={time(9, 0): time(8, 55)},  # Only 09:00 is mapped
        )
    ]

    result = apply_time_adjustments([lesson], adjustments)

    assert result[0].start == start


def test_multiple_rules_first_match_applies():
    """When multiple rules match, the first matching rule applies"""
    start = datetime(2025, 10, 6, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))  # Monday
    end = start + timedelta(hours=1)
    lesson = DummyLesson(start, end)

    adjustments = [
        TimeAdjustment(
            weekdays=[1, 2, 4, 5],
            start_times={time(9, 0): time(8, 55)},
        ),
        TimeAdjustment(
            weekdays=[1, 2, 4, 5],
            start_times={time(9, 0): time(8, 50)},  # Different adjustment
        ),
    ]

    result = apply_time_adjustments([lesson], adjustments)

    # First rule should apply
    assert result[0].start.strftime("%H:%M") == "08:55"


def test_sunday_as_seven():
    """Sunday is specified as 7"""
    start = datetime(2025, 10, 5, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))  # Sunday
    end = start + timedelta(hours=1)
    lesson = DummyLesson(start, end)

    adjustments = [
        TimeAdjustment(
            weekdays=[7],  # Sunday as 7
            start_times={time(9, 0): time(8, 55)},
        )
    ]

    result = apply_time_adjustments([lesson], adjustments)

    assert result[0].start.strftime("%H:%M") == "08:55"


def test_time_adjustment_with_varied_formats():
    """Time adjustment should handle different time formats (H:MM and HH:MM)"""
    start = datetime(2025, 10, 6, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))  # Monday
    end = start + timedelta(hours=1)
    lesson = DummyLesson(start, end)

    adjustments = [
        TimeAdjustment(
            weekdays=[1],
            start_times={time(9, 0): time(8, 58)},  # Single digit hour
        )
    ]

    result = apply_time_adjustments([lesson], adjustments)

    assert result[0].start.strftime("%H:%M") == "08:58"


def test_multiple_lessons_all_adjusted():
    """All lessons should be adjusted if they match the rules"""
    start1 = datetime(2025, 10, 6, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))  # Monday
    end1 = start1 + timedelta(hours=1)
    lesson1 = DummyLesson(start1, end1)

    start2 = datetime(2025, 10, 7, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))  # Tuesday
    end2 = start2 + timedelta(hours=1)
    lesson2 = DummyLesson(start2, end2)

    adjustments = [
        TimeAdjustment(
            weekdays=[1, 2, 4, 5],
            start_times={time(9, 0): time(8, 55)},
        )
    ]

    result = apply_time_adjustments([lesson1, lesson2], adjustments)

    assert len(result) == 2
    assert result[0].start.strftime("%H:%M") == "08:55"
    assert result[1].start.strftime("%H:%M") == "08:55"


def test_multiple_time_mappings_in_single_rule():
    """A single rule can have multiple time mappings"""
    start = datetime(2025, 10, 6, 10, 0, tzinfo=ZoneInfo("Europe/Paris"))  # Monday
    end = start + timedelta(hours=1)
    lesson = DummyLesson(start, end)

    adjustments = [
        TimeAdjustment(
            weekdays=[1, 2, 4, 5],
            start_times={
                time(9, 0): time(8, 55),
                time(10, 0): time(9, 55),
            },
            end_times={
                time(10, 0): time(10, 5),
                time(11, 0): time(11, 5),
            },
        )
    ]

    result = apply_time_adjustments([lesson], adjustments)

    # 10:00 start should be adjusted to 09:55
    assert result[0].start.strftime("%H:%M") == "09:55"


def test_preserves_timezone_after_adjustment():
    """Timezone information should be preserved after adjustment"""
    tz = ZoneInfo("Europe/Paris")
    start = datetime(2025, 10, 6, 9, 0, tzinfo=tz)
    end = start + timedelta(hours=1)
    lesson = DummyLesson(start, end)

    adjustments = [
        TimeAdjustment(
            weekdays=[1],
            start_times={time(9, 0): time(8, 55)},
        )
    ]

    result = apply_time_adjustments([lesson], adjustments)

    assert result[0].start.tzinfo == tz
    assert result[0].end.tzinfo == tz


def test_complex_scenario_from_config():
    """Test with muultiple rules and varied adjustments as per a realistic config"""
    # Monday 09:00-10:00
    monday_start = datetime(2025, 10, 6, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))
    monday_end = datetime(2025, 10, 6, 10, 0, tzinfo=ZoneInfo("Europe/Paris"))
    lesson_monday = DummyLesson(monday_start, monday_end)

    # Tuesday 10:00-11:00
    tuesday_start = datetime(2025, 10, 7, 10, 0, tzinfo=ZoneInfo("Europe/Paris"))
    tuesday_end = datetime(2025, 10, 7, 11, 0, tzinfo=ZoneInfo("Europe/Paris"))
    lesson_tuesday = DummyLesson(tuesday_start, tuesday_end)

    # Wednesday 09:00-10:00
    wednesday_start = datetime(2025, 10, 8, 9, 0, tzinfo=ZoneInfo("Europe/Paris"))
    wednesday_end = datetime(2025, 10, 8, 10, 0, tzinfo=ZoneInfo("Europe/Paris"))
    lesson_wednesday = DummyLesson(wednesday_start, wednesday_end)

    adjustments = [
        TimeAdjustment(
            weekdays=[1, 2, 4, 5],
            start_times={time(9, 0): time(8, 55), time(10, 0): time(9, 55)},
            end_times={time(10, 0): time(10, 5), time(11, 0): time(11, 5)},
        ),
        TimeAdjustment(
            weekdays=[3],
            start_times={time(9, 0): time(8, 58)},
        ),
    ]

    result = apply_time_adjustments(
        [lesson_monday, lesson_tuesday, lesson_wednesday], adjustments
    )

    # Monday: 09:00 -> 08:55, 10:00 -> 10:05
    assert result[0].start.strftime("%H:%M") == "08:55"
    assert result[0].end.strftime("%H:%M") == "10:05"

    # Tuesday: 10:00 -> 09:55, 11:00 -> 11:05
    assert result[1].start.strftime("%H:%M") == "09:55"
    assert result[1].end.strftime("%H:%M") == "11:05"

    # Wednesday: 09:00 -> 08:58, 10:00 unchanged
    assert result[2].start.strftime("%H:%M") == "08:58"
    assert result[2].end.strftime("%H:%M") == "10:00"
