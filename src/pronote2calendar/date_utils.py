from datetime import date, datetime, timedelta


def compute_sync_period(
    weeks: int | None = None, start: date | None = None
) -> tuple[datetime, datetime]:
    if weeks is None:
        weeks = 3

    if start is None:
        start = date.today()

    monday = start - timedelta(days=start.weekday())
    start = datetime.combine(monday, datetime.min.time()).astimezone()

    end = start + timedelta(weeks=weeks, seconds=-1)

    return start, end
