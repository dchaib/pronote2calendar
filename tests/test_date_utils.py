from datetime import date, timedelta

from pronote2calendar.date_utils import compute_sync_period


def test_compute_sync_period_default_weeks():
    # 2025-11-01 is a Saturday; the Monday of that week is 2025-10-27
    start = date(2025, 11, 1)
    start, end = compute_sync_period(start=start)

    # start should be midnight and timezone-aware
    assert (
        start.time().hour == 0 and start.time().minute == 0 and start.time().second == 0
    )
    assert start.tzinfo is not None

    # duration should be exactly 3 weeks minus 1 second
    assert end - start == timedelta(weeks=3, seconds=-1)

    # end should be 23:59:59
    assert end.time().hour == 23 and end.time().minute == 59 and end.time().second == 59
    assert end.tzinfo is not None


def test_compute_sync_period_custom_weeks():
    start = date(2025, 11, 1)
    start, end = compute_sync_period(1, start=start)

    assert end - start == timedelta(weeks=1, seconds=-1)
