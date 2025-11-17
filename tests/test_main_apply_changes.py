from pronote2calendar import main as main_mod


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


def make_config():
    return {"pronote": {}, "google_calendar": {}}


def run_main_with_changes(monkeypatch, changes_value):
    # Patch read_config and setup_logging
    monkeypatch.setattr(main_mod, "read_config", lambda: make_config())
    monkeypatch.setattr(main_mod, "setup_logging", lambda level: None)

    # Patch PronoteClient and GoogleCalendarClient
    monkeypatch.setattr(main_mod, "PronoteClient", lambda *a, **k: DummyPronote())
    dummy_cal = DummyCalendar()
    monkeypatch.setattr(main_mod, "GoogleCalendarClient", lambda *a, **k: dummy_cal)

    # Patch change_detection.get_changes
    monkeypatch.setattr(
        main_mod.change_detection, "get_changes", lambda lessons, events: changes_value
    )

    # Run main
    main_mod.main()

    return dummy_cal


def test_main_skips_apply_when_no_changes(monkeypatch):
    dummy_cal = run_main_with_changes(monkeypatch, {})
    assert not dummy_cal.applied


def test_main_applies_when_changes_present(monkeypatch):
    changes = {"add": [{"summary": "Test"}], "remove": [], "update": []}
    dummy_cal = run_main_with_changes(monkeypatch, changes)
    assert dummy_cal.applied
