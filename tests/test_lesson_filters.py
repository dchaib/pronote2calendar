import logging
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pronotepy
import pytest

from pronote2calendar import main as main_mod
from pronote2calendar.lesson_filters import filter_lessons
from pronote2calendar.models import CalendarEvent
from pronote2calendar.pronote_client import PronoteClient
from pronote2calendar.settings import (
    AjustmentsSettings,
    EventsSettings,
    FiltersSettings,
    NotificationsSettings,
    Settings,
    SyncSettings,
)


def make_lesson(name="PERMANENCE", hour=9, num=1):
    contents = [] if name is None else [{"G": 16, "N": name, "L": name}]
    return pronotepy.Lesson(
        Mock(),
        {
            "N": str(num),
            "P": num,
            "DateDuCours": {"V": f"12/11/2026 {hour:02}:00:00"},
            "DateDuCoursFin": {"V": f"12/11/2026 {hour + 1:02}:00:00"},
            "ListeContenus": {"V": contents},
        },
    )


@pytest.mark.parametrize("excluded", [[], ["PERMANENCE", "VIE DE CLASSE"]])
def test_filter_preserves_order_and_objects(excluded):
    lessons = [
        make_lesson(name)
        for name in ["Math", "PERMANENCE", None, "VIE DE CLASSE", "Math"]
    ]
    original = list(lessons)
    result = filter_lessons(lessons, FiltersSettings(excluded_subjects=excluded))
    expected = [lessons[0], lessons[2], lessons[4]] if excluded else lessons
    assert result == expected
    assert all(
        actual is expected for actual, expected in zip(result, expected, strict=True)
    )
    assert lessons == original
    assert lessons[1].subject.name == "PERMANENCE"


@pytest.mark.parametrize(
    "name", ["permanence", " PERMANENCE", "PERMANENCE ", "PERMANENCE"]
)
def test_matching_is_exact(name):
    lesson = make_lesson(name)
    result = filter_lessons([lesson], FiltersSettings(excluded_subjects=["PERMANENCE"]))
    assert result == ([] if name == "PERMANENCE" else [lesson])


def test_empty_lessons():
    assert filter_lessons([], FiltersSettings(excluded_subjects=["PERMANENCE"])) == []


def test_logs_exclusions(caplog):
    with caplog.at_level(logging.DEBUG, logger="pronote2calendar.lesson_filters"):
        filter_lessons(
            [make_lesson()], FiltersSettings(excluded_subjects=["PERMANENCE"])
        )
    assert "Excluded 1 of 1 lessons by subject" in caplog.text
    assert "'PERMANENCE' starting at 2026-11-12 09:00:00" in caplog.text


@pytest.mark.parametrize("excluded", [[], ["PERMANENCE", "VIE DE CLASSE"]])
def test_filters_loaded_from_yaml(tmp_path, monkeypatch, excluded):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.yaml").write_text(
        "google_calendar:\n  calendar_id: test@example.com\n"
        f"filters:\n  excluded_subjects: {excluded!r}\n"
    )
    config = Settings()  # type: ignore[call-arg]
    assert config.filters.excluded_subjects == excluded


def test_main_filters_before_adjustments_and_removes_exported_lesson(monkeypatch):
    # The newest version replaces an older course at the same time.
    lessons = [
        make_lesson("Math", num=1),
        make_lesson(num=2),
        make_lesson("Math", hour=10),
    ]
    pronote = PronoteClient.__new__(PronoteClient)
    pronote.client = Mock(logged_in=True)
    pronote.client.lessons.return_value = lessons
    pronote.timezone = ZoneInfo("Europe/Paris")
    start = datetime(2026, 11, 12, 9, tzinfo=pronote.timezone)
    middle = start.replace(hour=10)
    end = start.replace(hour=11)
    permanence = CalendarEvent("permanence", start, middle, "PERMANENCE")
    retained = CalendarEvent("math", middle, end, "Maths")
    calendar = Mock()
    calendar.get_events.return_value = [permanence, retained]
    config = SimpleNamespace(
        log_level="INFO",
        sync=SyncSettings(),
        filters=FiltersSettings(excluded_subjects=["PERMANENCE"]),
        adjustments=AjustmentsSettings(
            subject={"PERMANENCE": "Étude", "Math": "Maths"}
        ),
        events=EventsSettings(),
        notifications=NotificationsSettings(),
        pronote=None,
        google_calendar=None,
    )
    monkeypatch.setattr(main_mod, "Settings", lambda: config)
    monkeypatch.setattr(main_mod, "setup_logging", lambda *a, **k: None)
    monkeypatch.setattr(main_mod, "PronoteClient", lambda *a, **k: pronote)
    monkeypatch.setattr(main_mod, "GoogleCalendarClient", lambda *a, **k: calendar)
    monkeypatch.setattr(main_mod, "compute_sync_period", lambda weeks: (start, end))

    def adjust_time(lessons, rules):
        assert len(lessons) == 1
        assert lessons[0].subject.name == "Math"
        return lessons

    monkeypatch.setattr(main_mod, "apply_time_adjustments", adjust_time)
    assert main_mod.main() == 0
    changes = calendar.apply_changes.call_args.args[0]
    assert changes.to_remove == [permanence]
    assert changes.to_add == []
    assert changes.to_update == []
