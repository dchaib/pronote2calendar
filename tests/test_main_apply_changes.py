from pronote2calendar import main as main_mod
from pronote2calendar.models import ChangeSet
from pronote2calendar.settings import (
    AjustmentsSettings,
    EventsSettings,
    FiltersSettings,
    NotificationsSettings,
    SyncSettings,
)

# retain the original Settings class so our helper can avoid overwriting it
_orig_Settings = main_mod.Settings


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
    monkeypatch.setattr(main_mod, "setup_logging", lambda *a, **k: None)

    # allow tests to patch Settings beforehand; only create a default if
    # nothing has been changed yet
    if main_mod.Settings is _orig_Settings:

        class MockSettings:
            log_level = "INFO"
            sync = SyncSettings(weeks=3)
            filters = FiltersSettings()
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
    dummy_cal.exit_code = main_mod.main()

    return dummy_cal


def test_main_sends_notifications_when_configured(monkeypatch):
    calls = []
    monkeypatch.setattr(
        main_mod, "send_notifications", lambda ns, ch: calls.append((ns, ch))
    )
    # prepare changes
    changes = ChangeSet([1], [], [])

    # override Settings to enable notifications and give a destination
    class MockSettingsEnabled:
        log_level = "INFO"
        sync = SyncSettings(weeks=3)
        filters = FiltersSettings()
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
    changes = ChangeSet([1], [], [])

    # override settings to have empty destinations list
    class MockSettings2:
        log_level = "INFO"
        sync = SyncSettings(weeks=3)
        filters = FiltersSettings()
        adjustments = AjustmentsSettings()
        events = EventsSettings()
        # even though destinations is empty we still turn notifications on
        notifications = NotificationsSettings(destinations=[], enabled=True)
        pronote = None
        google_calendar = None

    monkeypatch.setattr(main_mod, "Settings", MockSettings2)
    run_main_with_changes(monkeypatch, changes)
    # should still call send_notifications; function should handle empty list internally
    assert len(calls) == 1
    assert calls[0][0].destinations == []


def test_main_skips_apply_when_no_changes(monkeypatch):
    changes = ChangeSet([], [], [])
    dummy_cal = run_main_with_changes(monkeypatch, changes)
    assert not dummy_cal.applied
    assert dummy_cal.exit_code == 0


def test_main_applies_when_changes_present(monkeypatch):
    changes = ChangeSet([1], [], [])
    dummy_cal = run_main_with_changes(monkeypatch, changes)
    assert dummy_cal.applied
    assert dummy_cal.exit_code == 0


def test_main_stops_before_writes_when_calendar_read_fails(monkeypatch, caplog):
    def fail_read(self, start, end):
        raise RuntimeError("calendar unavailable")

    monkeypatch.setattr(DummyCalendar, "get_events", fail_read)
    calendar = run_main_with_changes(monkeypatch, ChangeSet([1], [], []))
    assert calendar.exit_code == 1
    assert not calendar.applied
    assert len([r for r in caplog.records if r.exc_info]) == 1


def test_login_failure_returns_error(monkeypatch):
    monkeypatch.setattr(DummyPronote, "is_logged_in", lambda self: False)
    calendar = run_main_with_changes(monkeypatch, ChangeSet([1], [], []))
    assert calendar.exit_code == 1
    assert not calendar.applied


def test_notification_failure_keeps_applied_changes(monkeypatch):
    monkeypatch.setattr(main_mod, "send_notifications", lambda *args: False)
    calendar = run_main_with_changes(monkeypatch, ChangeSet([1], [], []))
    assert calendar.applied
    assert calendar.exit_code == 1


def test_configuration_error_returns_error_without_traceback(monkeypatch, caplog):
    def invalid_settings():
        raise ValueError("invalid configuration")

    monkeypatch.setattr(main_mod, "Settings", invalid_settings)
    monkeypatch.setattr(main_mod, "setup_logging", lambda *args, **kwargs: None)
    assert main_mod.main() == 1
    assert len(caplog.records) == 1
    assert not caplog.records[0].exc_info
