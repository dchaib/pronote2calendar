import tempfile
from datetime import time
from pathlib import Path

import pytest
from pydantic import ValidationError

from pronote2calendar.settings import (
    GoogleCalendarSettings,
    PronoteSettings,
    Settings,
    SyncSettings,
    TimeAdjustment,
    normalize_time,
)


class TestNormalizeTime:
    """Test the normalize_time function."""

    def test_normalize_single_digit_hour_with_minutes(self):
        """Test that single-digit hours get padded with a leading zero."""
        assert normalize_time("8:00") == "08:00"
        assert normalize_time("9:30") == "09:30"
        assert normalize_time("5:15") == "05:15"

    def test_normalize_single_digit_hour_without_minutes(self):
        """Test that single-digit hours without minutes get padded."""
        assert normalize_time("8") == "08"
        assert normalize_time("9") == "09"
        assert normalize_time("5") == "05"

    def test_normalize_double_digit_hour_unchanged(self):
        """Test that double-digit hours remain unchanged."""
        assert normalize_time("08:00") == "08:00"
        assert normalize_time("14:30") == "14:30"
        assert normalize_time("23:59") == "23:59"

    def test_normalize_with_whitespace(self):
        """Test that whitespace is stripped before normalization."""
        assert normalize_time("  8:00  ") == "08:00"
        assert normalize_time("\t9:30\t") == "09:30"

    def test_normalize_non_digit_hour(self):
        """Test that non-digit hours are returned unchanged."""
        assert normalize_time("a:00") == "a:00"
        assert normalize_time("abc") == "abc"

    def test_normalize_non_string_values(self):
        """Test that non-string values are returned unchanged."""
        assert normalize_time(time(8, 0)) == time(8, 0)
        assert normalize_time(123) == 123
        assert normalize_time(None) is None

    def test_normalize_empty_string(self):
        """Test that empty string is returned unchanged."""
        assert normalize_time("") == ""

    def test_normalize_colon_only(self):
        """Test that colon-only strings are returned unchanged."""
        assert normalize_time(":") == ":"


class TestPronoteSettings:
    """Test the PronoteSettings class."""

    def test_default_values(self):
        """Test that PronoteSettings has correct default values."""
        settings = PronoteSettings()
        assert settings.connection_type == "token"
        assert settings.account_type == "child"
        assert settings.child is None

    def test_custom_values(self):
        """Test that PronoteSettings accepts custom values."""
        settings = PronoteSettings(
            connection_type="password", account_type="parent", child="John"
        )
        assert settings.connection_type == "password"
        assert settings.account_type == "parent"
        assert settings.child == "John"

    def test_connection_type_validation(self):
        """Test that connection_type only accepts 'token' or 'password'."""
        with pytest.raises(ValidationError):
            PronoteSettings(connection_type="invalid")

    def test_account_type_validation(self):
        """Test that account_type only accepts 'child' or 'parent'."""
        with pytest.raises(ValidationError):
            PronoteSettings(account_type="invalid")

    def test_parent_without_child_fails(self):
        """Test that 'parent' account_type requires a child."""
        with pytest.raises(ValidationError) as exc_info:
            PronoteSettings(account_type="parent")
        assert "'child' is required when 'account_type' is 'parent'" in str(
            exc_info.value
        )

    def test_parent_with_empty_child_fails(self):
        """Test that 'parent' account_type requires a non-empty child."""
        with pytest.raises(ValidationError) as exc_info:
            PronoteSettings(account_type="parent", child="")
        assert "'child' is required when 'account_type' is 'parent'" in str(
            exc_info.value
        )

    def test_parent_with_whitespace_child_fails(self):
        """Test that 'parent' account_type requires a non-whitespace child."""
        with pytest.raises(ValidationError) as exc_info:
            PronoteSettings(account_type="parent", child="   ")
        assert "'child' is required when 'account_type' is 'parent'" in str(
            exc_info.value
        )

    def test_parent_with_valid_child_succeeds(self):
        """Test that 'parent' account_type with a valid child passes."""
        settings = PronoteSettings(account_type="parent", child="Alice")
        assert settings.account_type == "parent"
        assert settings.child == "Alice"

    def test_child_account_ignores_child_field(self):
        """Test that 'child' account_type works even without a child specified."""
        settings = PronoteSettings(account_type="child")
        assert settings.account_type == "child"
        assert settings.child is None


class TestGoogleCalendarSettings:
    """Test the GoogleCalendarSettings class."""

    def test_calendar_id_required(self):
        """Test that calendar_id is required."""
        with pytest.raises(ValidationError):
            GoogleCalendarSettings()

    def test_calendar_id_provided(self):
        """Test that GoogleCalendarSettings accepts a calendar_id."""
        settings = GoogleCalendarSettings(calendar_id="my-calendar@gmail.com")
        assert settings.calendar_id == "my-calendar@gmail.com"


class TestSyncSettings:
    """Test the SyncSettings class."""

    def test_default_weeks(self):
        """Test that SyncSettings has a default weeks value of 3."""
        settings = SyncSettings()
        assert settings.weeks == 3

    def test_custom_weeks(self):
        """Test that SyncSettings accepts a custom weeks value."""
        settings = SyncSettings(weeks=5)
        assert settings.weeks == 5

    def test_weeks_zero(self):
        """Test that SyncSettings accepts 0 weeks."""
        settings = SyncSettings(weeks=0)
        assert settings.weeks == 0

    def test_negative_weeks_fails(self):
        """Test that SyncSettings rejects negative weeks."""
        with pytest.raises(ValidationError):
            SyncSettings(weeks=-1)


class TestTimeAdjustment:
    """Test the TimeAdjustment class."""

    def test_weekdays_required(self):
        """Test that weekdays is required."""
        with pytest.raises(ValidationError):
            TimeAdjustment()

    def test_valid_weekdays(self):
        """Test that TimeAdjustment accepts valid weekday values."""
        settings = TimeAdjustment(weekdays=[1, 2, 3, 4, 5])
        assert settings.weekdays == [1, 2, 3, 4, 5]

    def test_empty_weekdays(self):
        """Test that TimeAdjustment accepts an empty weekdays list."""
        settings = TimeAdjustment(weekdays=[])
        assert settings.weekdays == []

    def test_default_times(self):
        """Test that TimeAdjustment has default empty time mappings."""
        settings = TimeAdjustment(weekdays=[1])
        assert settings.start_times == {}
        assert settings.end_times == {}

    def test_custom_start_times(self):
        """Test that TimeAdjustment accepts custom start_times."""
        start_times = {time(8, 0): time(8, 30), time(14, 0): time(14, 15)}
        settings = TimeAdjustment(weekdays=[1, 2], start_times=start_times)
        assert settings.start_times == start_times

    def test_custom_end_times(self):
        """Test that TimeAdjustment accepts custom end_times."""
        end_times = {time(17, 0): time(17, 30)}
        settings = TimeAdjustment(weekdays=[1, 2], end_times=end_times)
        assert settings.end_times == end_times

    def test_both_time_mappings(self):
        """Test that TimeAdjustment can have both start and end times."""
        start_times = {time(8, 0): time(8, 30)}
        end_times = {time(17, 0): time(17, 30)}
        settings = TimeAdjustment(
            weekdays=[1], start_times=start_times, end_times=end_times
        )
        assert settings.start_times == start_times
        assert settings.end_times == end_times

    def test_weekdays_valid_range(self):
        """Test that weekdays accepts valid values 1-7."""
        for day in range(1, 8):
            settings = TimeAdjustment(weekdays=[day])
            assert day in settings.weekdays

    def test_weekdays_below_range(self):
        """Test that weekdays rejects values below 1."""
        with pytest.raises(ValidationError) as exc_info:
            TimeAdjustment(weekdays=[0])
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_weekdays_above_range(self):
        """Test that weekdays rejects values above 7."""
        with pytest.raises(ValidationError) as exc_info:
            TimeAdjustment(weekdays=[8])
        assert "less than or equal to 7" in str(exc_info.value)

    def test_weekdays_mixed_valid_and_invalid(self):
        """Test that TimeAdjustment rejects if any weekday is invalid."""
        with pytest.raises(ValidationError) as exc_info:
            TimeAdjustment(weekdays=[1, 2, 8])
        assert "less than or equal to 7" in str(exc_info.value)

    def test_flexible_time_single_digit_hour_in_start_times(self):
        """Test that single-digit hours can be used in start_times keys."""
        start_times = {"8:00": "8:30", "9:15": "9:45"}
        settings = TimeAdjustment(weekdays=[1], start_times=start_times)
        assert time(8, 0) in settings.start_times
        assert time(9, 15) in settings.start_times
        assert settings.start_times[time(8, 0)] == time(8, 30)
        assert settings.start_times[time(9, 15)] == time(9, 45)

    def test_flexible_time_single_digit_hour_in_end_times(self):
        """Test that single-digit hours can be used in end_times keys."""
        end_times = {"5:00": "5:15", "9:30": "9:45"}
        settings = TimeAdjustment(weekdays=[1], end_times=end_times)
        assert time(5, 0) in settings.end_times
        assert time(9, 30) in settings.end_times
        assert settings.end_times[time(5, 0)] == time(5, 15)
        assert settings.end_times[time(9, 30)] == time(9, 45)

    def test_flexible_time_mixed_single_and_double_digit_hours(self):
        """Test that both single and double digit hours work together."""
        start_times = {"8:00": "8:30", "14:00": "14:15"}
        settings = TimeAdjustment(weekdays=[1], start_times=start_times)
        assert time(8, 0) in settings.start_times
        assert time(14, 0) in settings.start_times
        assert settings.start_times[time(8, 0)] == time(8, 30)
        assert settings.start_times[time(14, 0)] == time(14, 15)


class TestSettings:
    """Test the Settings class."""

    def test_google_calendar_required(self):
        """Test that google_calendar is required."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text("")

            with pytest.raises(ValidationError):
                Settings(
                    _env_file=config_path,
                )

    def test_default_values_with_minimal_config(self):
        """Test that Settings has correct defaults with minimal config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text("google_calendar:\n  calendar_id: test@gmail.com\n")

            # Create a temporary settings file
            original_cwd = Path.cwd()
            try:
                import os

                os.chdir(tmpdir)
                settings = Settings()
                assert settings.google_calendar.calendar_id == "test@gmail.com"
                assert settings.pronote.connection_type == "token"
                assert settings.pronote.account_type == "child"
                assert settings.sync.weeks == 3
                assert settings.log_level == "INFO"
                assert settings.time_adjustments == []
            finally:
                os.chdir(original_cwd)

    def test_custom_log_level(self):
        """Test that Settings accepts custom log_level."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text(
                "google_calendar:\n  calendar_id: test@gmail.com\nlog_level: DEBUG\n"
            )

            original_cwd = Path.cwd()
            try:
                import os

                os.chdir(tmpdir)
                settings = Settings()
                assert settings.log_level == "DEBUG"
            finally:
                os.chdir(original_cwd)

    def test_nested_pronote_settings(self):
        """Test that Settings can have nested PronoteSettings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text(
                """
google_calendar:
  calendar_id: test@gmail.com
pronote:
  connection_type: password
  account_type: parent
  child: Alice
"""
            )

            original_cwd = Path.cwd()
            try:
                import os

                os.chdir(tmpdir)
                settings = Settings()
                assert settings.pronote.connection_type == "password"
                assert settings.pronote.account_type == "parent"
                assert settings.pronote.child == "Alice"
            finally:
                os.chdir(original_cwd)

    def test_nested_sync_settings(self):
        """Test that Settings can have nested SyncSettings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text(
                """
google_calendar:
  calendar_id: test@gmail.com
sync:
  weeks: 5
"""
            )

            original_cwd = Path.cwd()
            try:
                import os

                os.chdir(tmpdir)
                settings = Settings()
                assert settings.sync.weeks == 5
            finally:
                os.chdir(original_cwd)

    def test_time_adjustments_list(self):
        """Test that Settings can have a list of TimeAdjustment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text(
                """
google_calendar:
  calendar_id: test@gmail.com
time_adjustments:
  - weekdays: [1, 2, 3]
  - weekdays: [4, 5]
"""
            )

            original_cwd = Path.cwd()
            try:
                import os

                os.chdir(tmpdir)
                settings = Settings()
                assert len(settings.time_adjustments) == 2
                assert settings.time_adjustments[0].weekdays == [1, 2, 3]
                assert settings.time_adjustments[1].weekdays == [4, 5]
            finally:
                os.chdir(original_cwd)

    def test_complex_configuration(self):
        """Test a complex configuration with all options."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text(
                """
google_calendar:
  calendar_id: my-calendar@gmail.com
pronote:
  connection_type: password
  account_type: parent
  child: Bob
sync:
  weeks: 4
log_level: DEBUG
time_adjustments:
  - weekdays: [1, 2, 3, 4, 5]
    start_times:
      "08:00": "08:30"
      "14:00": "14:15"
    end_times:
      "17:00": "17:30"
"""
            )

            original_cwd = Path.cwd()
            try:
                import os

                os.chdir(tmpdir)
                settings = Settings()
                assert settings.google_calendar.calendar_id == "my-calendar@gmail.com"
                assert settings.pronote.connection_type == "password"
                assert settings.pronote.account_type == "parent"
                assert settings.pronote.child == "Bob"
                assert settings.sync.weeks == 4
                assert settings.log_level == "DEBUG"
                assert len(settings.time_adjustments) == 1
                assert settings.time_adjustments[0].weekdays == [1, 2, 3, 4, 5]
                assert time(8, 0) in settings.time_adjustments[0].start_times
                assert time(14, 0) in settings.time_adjustments[0].start_times
                assert time(17, 0) in settings.time_adjustments[0].end_times
            finally:
                os.chdir(original_cwd)

    def test_single_digit_hour_times_in_config(self):
        """Test that single-digit hours (e.g., '8:00') work in YAML config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_path.write_text(
                """
google_calendar:
  calendar_id: my-calendar@gmail.com
time_adjustments:
  - weekdays: [1, 2, 3]
    start_times:
      "8:00": "8:30"
      "9:15": "9:45"
    end_times:
      "5:00": "5:15"
      "17:30": "17:45"
"""
            )

            original_cwd = Path.cwd()
            try:
                import os

                os.chdir(tmpdir)
                settings = Settings()
                assert len(settings.time_adjustments) == 1
                adj = settings.time_adjustments[0]
                # Single-digit times should be normalized and parsed correctly
                assert time(8, 0) in adj.start_times
                assert time(9, 15) in adj.start_times
                assert time(5, 0) in adj.end_times
                assert time(17, 30) in adj.end_times
                # Check the mapped values
                assert adj.start_times[time(8, 0)] == time(8, 30)
                assert adj.start_times[time(9, 15)] == time(9, 45)
                assert adj.end_times[time(5, 0)] == time(5, 15)
                assert adj.end_times[time(17, 30)] == time(17, 45)
            finally:
                os.chdir(original_cwd)
