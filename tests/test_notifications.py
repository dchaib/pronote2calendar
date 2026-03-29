from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from pronote2calendar.models import CalendarEvent, ChangeSet, LessonEvent
from pronote2calendar.notifications import send_notifications
from pronote2calendar.settings import NotificationsSettings, NotificationsTemplates


class DummyApprise:
    def __init__(self):
        self.urls = []
        self.notified = False
        self.last = {}

    def add(self, url):
        self.urls.append(url)

    def notify(self, title=None, body=None):
        self.notified = True
        self.last = {"title": title, "body": body}


@pytest.fixture(autouse=True)
def patch_apprise(monkeypatch):
    """Replace apprise.Apprise with dummy object."""
    monkeypatch.setattr(
        "pronote2calendar.notifications.Apprise", lambda: DummyApprise()
    )
    yield


def make_event(start_offset_days: int, base_now=None) -> LessonEvent:
    base = base_now or datetime.now(ZoneInfo("UTC"))
    start = base + timedelta(days=start_offset_days)
    end = start + timedelta(hours=1)
    return LessonEvent(start, end, "S", "D", "L")


def test_no_destinations_list(monkeypatch):
    ns = NotificationsSettings(destinations=[], max_delay_days=5)
    changes = ChangeSet([], [], [])
    # Should not raise even when notifications disabled
    send_notifications(ns, changes)


def test_disabled(monkeypatch):
    ns = NotificationsSettings(destinations=["any"], enabled=False)
    changes = ChangeSet([make_event(0)], [], [])
    called = []

    class Cap(DummyApprise):
        def notify(self, title=None, body=None):
            called.append(True)

    monkeypatch.setattr("pronote2calendar.notifications.Apprise", lambda: Cap())
    send_notifications(ns, changes)
    assert not called


def test_filtering_by_delay(monkeypatch):
    # prepare settings with one url
    ns = NotificationsSettings(destinations=["test"], max_delay_days=2, enabled=True)
    now = datetime(2026, 3, 1, tzinfo=ZoneInfo("UTC"))
    # create three events: one within 1 day, one at 0 (update), one beyond limit
    a_within = make_event(1, now)
    a_out = make_event(3, now)
    # create a simple update diff; old event differs in summary
    update_ev = make_event(0, now)
    from pronote2calendar.models import UpdateDiff

    diff = UpdateDiff(
        id="x",
        old=CalendarEvent(
            id="event_id",
            start=update_ev.start,
            end=update_ev.end,
            summary="old",
            location="",
            description="",
        ),
        new=update_ev,
        changes={"summary": ("old", update_ev.summary)},
    )
    remove_ev = make_event(1, now)
    remove_ev.summary = "R"
    changes = ChangeSet([a_within, a_out], [diff], [remove_ev])
    captured = {}

    class Cap(DummyApprise):
        def notify(self, title=None, body=None):
            captured["title"] = title
            captured["body"] = body
            self.notified = True

    monkeypatch.setattr("pronote2calendar.notifications.Apprise", lambda: Cap())
    send_notifications(ns, changes, now=now)

    # ensure notify was called and body contains only the within-limit entries
    assert captured
    assert "Added" in captured["body"]
    assert "R" in captured["body"]  # removal at day1 still within
    # ensure event beyond limit is not present
    assert str(a_out.start) not in captured["body"]


def test_no_notification_if_all_out_of_range():
    ns = NotificationsSettings(destinations=["u"], max_delay_days=1, enabled=True)
    now = datetime(2026, 3, 1, tzinfo=ZoneInfo("UTC"))
    ev = make_event(5)
    changes = ChangeSet([ev], [], [])
    # using dummy apprise, but we need to capture
    notified = []

    class CapturingApprise(DummyApprise):
        def notify(self, title=None, body=None):
            notified.append((title, body))

    import pronote2calendar.notifications as notif_mod

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(notif_mod, "Apprise", lambda: CapturingApprise())
    try:
        send_notifications(ns, changes, now=now)
    finally:
        monkeypatch.undo()
    assert not notified


def test_template_rendering(monkeypatch):
    ns = NotificationsSettings(
        destinations=["url"],
        enabled=True,
        max_delay_days=10,
        templates=NotificationsTemplates(
            title="T {{ adds|length }}", body="B {{ updates|length }}"
        ),
    )
    now = datetime(2026, 3, 1, tzinfo=ZoneInfo("UTC"))
    a = make_event(0, now)
    # create an update diff from a to itself just to exercise the code path
    from pronote2calendar.models import UpdateDiff

    diff = UpdateDiff(
        id="event_id",
        old=CalendarEvent(
            id="event_id",
            start=a.start,
            end=a.end,
            summary=a.summary,
            description=a.description,
            location=a.location,
        ),
        new=a,
        changes={},
    )
    changes = ChangeSet([a], [diff], [])
    # capture notification
    captured = {}

    class Cap(DummyApprise):
        def notify(self, title=None, body=None):
            captured["title"] = title
            captured["body"] = body

    monkeypatch.setattr("pronote2calendar.notifications.Apprise", lambda: Cap())
    send_notifications(ns, changes, now=now)
    assert captured["title"] == "T 1"
    assert captured["body"] == "B 1"


def test_default_template_includes_diff_details(monkeypatch):
    # ensure that the default body uses old/new information for updates
    ns = NotificationsSettings(destinations=["url"], enabled=True, max_delay_days=10)
    now = datetime(2026, 3, 1, tzinfo=ZoneInfo("UTC"))
    # build a change set using get_changes to guarantee proper diff
    from pronote2calendar.change_detection import get_changes

    old_event = CalendarEvent(
        id="u1",
        summary="English",
        start=now,
        end=now + timedelta(hours=1),
        location="Room A",
        description="Mr X",
    )
    new_event = LessonEvent(
        start=now,
        end=now + timedelta(hours=1),
        summary="French",
        description="Mrs X",
        location="Room A",
    )
    changes = get_changes([new_event], [old_event])

    captured = {}

    class Cap(DummyApprise):
        def notify(self, title=None, body=None):
            captured["title"] = title
            captured["body"] = body

    monkeypatch.setattr("pronote2calendar.notifications.Apprise", lambda: Cap())
    send_notifications(ns, changes, now=now)
    assert "Updated" in captured["body"]
    assert "English" in captured["body"]
    assert "French" in captured["body"]
    # the diff should include the old value as well as the new one
    assert "Mr X" in captured["body"]
