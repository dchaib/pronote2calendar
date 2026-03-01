from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from pronote2calendar.change_detection import ChangeSet
from pronote2calendar.event_creator import LessonEvent
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


def make_event(start_offset_days: int):
    start = datetime.now(ZoneInfo("UTC")) + timedelta(days=start_offset_days)
    end = start + timedelta(hours=1)
    return LessonEvent(start, end, "S", "D", "L")


def test_no_destinations_list(monkeypatch):
    ns = NotificationsSettings(destinations=[], max_delay_days=5)
    changes = ChangeSet([], {}, [])
    # Should not raise even when notifications disabled
    send_notifications(ns, changes)


def test_disabled(monkeypatch):
    ns = NotificationsSettings(destinations=["any"], enabled=False)
    changes = ChangeSet([make_event(0)], {}, [])
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
    a_within = make_event(1)
    a_out = make_event(3)
    update_ev = make_event(0)
    remove_ev = {
        "summary": "R",
        "start": {"dateTime": (now + timedelta(days=1)).isoformat()},
    }
    changes = ChangeSet([a_within, a_out], {"x": update_ev}, [remove_ev])
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
    changes = ChangeSet([ev], {}, [])
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
    a = make_event(0)
    changes = ChangeSet([a], {"k": a}, [])
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
