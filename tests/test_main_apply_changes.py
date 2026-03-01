from pronote2calendar import main as main_mod
from pronote2calendar.change_detection import ChangeSet
from pronote2calendar.settings import (
    AjustmentsSettings,
    EventsSettings,
    NotificationsSettings,
    SyncSettings,
)


class DummyCalendar:
    def __init__(self):
        self.applied = False

    def get_events(self, start, end):
        return []

    def apply_changes(self, changes):
        self.applied = True


class DummyPronote:
    def __init__(self):
        pass

    def is_logged_in(self):
        return True

    def get_lessons(self, start, end):
        return []


def run_main_with_changes(monkeypatch, changes_value):
    # Patch setup_logging
    monkeypatch.setattr(main_mod, "setup_logging", lambda level: None)

    # Create a mock Settings object
    class MockSettings:
        log_level = "INFO"
        sync = SyncSettings(weeks=3)
        adjustments = AjustmentsSettings()
        events = EventsSettings()
        notifications = NotificationsSettings()  # new field
        pronote = None
        google_calendar = None

    monkeypatch.setattr(main_mod, "Settings", MockSettings)

    # Patch PronoteClient and GoogleCalendarClient
    monkeypatch.setattr(main_mod, "PronoteClient", lambda *a, **k: DummyPronote())
    dummy_cal = DummyCalendar()
    monkeypatch.setattr(main_mod, "GoogleCalendarClient", lambda *a, **k: dummy_cal)

    # Patch change_detection.get_changes
    monkeypatch.setattr(
        main_mod.change_detection,
        "get_changes",
        lambda existing, new: changes_value,
    )

    # Run main
    main_mod.main()

    return dummy_cal


def test_main_sends_notifications_when_configured(monkeypatch):
    calls = []
    monkeypatch.setattr(
        main_mod, "send_notifications", lambda ns, ch: calls.append((ns, ch))
    )
    # prepare changes
    changes = ChangeSet([1], {}, [])

    # override Settings to enable notifications and give a destination
    class MockSettingsEnabled:
        log_level = "INFO"
        sync = SyncSettings(weeks=3)
        adjustments = AjustmentsSettings()
        events = EventsSettings()
        notifications = NotificationsSettings(destinations=["dummy"], enabled=True)
        pronote = None
        google_calendar = None

    monkeypatch.setattr(main_mod, "Settings", MockSettingsEnabled)

    run_main_with_changes(monkeypatch, changes)
    assert calls, "send_notifications should have been called"


def test_main_skips_notifications_when_empty(monkeypatch):
    calls = []
    monkeypatch.setattr(
        main_mod, "send_notifications", lambda ns, ch: calls.append((ns, ch))
    )
    changes = ChangeSet([1], {}, [])

    # override settings to have empty destinations list
    class MockSettings2:
        log_level = "INFO"
        sync = SyncSettings(weeks=3)
        adjustments = AjustmentsSettings()
        events = EventsSettings()
        notifications = NotificationsSettings(destinations=[])
        pronote = None
        google_calendar = None

    monkeypatch.setattr(main_mod, "Settings", MockSettings2)
    run_main_with_changes(monkeypatch, changes)
    # should still call send_notifications; function should handle empty list internally
    assert len(calls) == 1
    assert calls[0][0].destinations == []


def test_main_skips_apply_when_no_changes(monkeypatch):
    changes = ChangeSet([], {}, [])
    dummy_cal = run_main_with_changes(monkeypatch, changes)
    assert not dummy_cal.applied


def test_main_applies_when_changes_present(monkeypatch):
    changes = ChangeSet([1], {}, [])
    dummy_cal = run_main_with_changes(monkeypatch, changes)
    assert dummy_cal.applied
