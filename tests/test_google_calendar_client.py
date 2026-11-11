from datetime import datetime
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest
from googleapiclient.errors import HttpError  # type: ignore
from httplib2 import Response  # type: ignore

from pronote2calendar.google_calendar_client import GoogleCalendarClient


def test_http_read_failure_propagates_instead_of_returning_empty_calendar():
    client = GoogleCalendarClient.__new__(GoogleCalendarClient)
    client.calendar_id = "test@example.com"
    client.service = Mock()
    error = HttpError(Response({"status": "503"}), b'{"error": "unavailable"}')
    client.service.events.return_value.list.return_value.execute.side_effect = error
    now = datetime.now(ZoneInfo("UTC"))
    with pytest.raises(HttpError):
        client.get_events(now, now)
