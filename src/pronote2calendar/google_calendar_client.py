import logging
from datetime import datetime
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build  # type: ignore
from googleapiclient.errors import HttpError  # type: ignore

from pronote2calendar.models import CalendarEvent, ChangeSet, LessonEvent
from pronote2calendar.settings import GoogleCalendarSettings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
]
EXTENDED_PROPERTY_SOURCE = "pronote2calendar"


def _event_from_calendar_dict(calendar_dict: dict[str, Any]) -> CalendarEvent:
    event_id = calendar_dict.get("id")
    if not isinstance(event_id, str):
        raise ValueError("Missing or invalid 'id'")

    start_raw = calendar_dict.get("start", {})
    end_raw = calendar_dict.get("end", {})

    start_str = start_raw.get("dateTime") or start_raw.get("date")
    end_str = end_raw.get("dateTime") or end_raw.get("date")

    if not isinstance(start_str, str) or not isinstance(end_str, str):
        raise ValueError("Missing or invalid start/end")

    return CalendarEvent(
        id=event_id,
        start=datetime.fromisoformat(start_str),
        end=datetime.fromisoformat(end_str),
        summary=calendar_dict.get("summary"),
        location=calendar_dict.get("location"),
        description=calendar_dict.get("description"),
    )


class GoogleCalendarClient:
    def __init__(self, config: GoogleCalendarSettings, credentials_file_path: str):
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file_path, scopes=SCOPES
        )
        self.service = build("calendar", "v3", credentials=credentials)
        self.calendar_id = config.calendar_id

    def get_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        try:
            events_result = (
                self.service.events()
                .list(
                    calendarId=self.calendar_id,
                    timeMin=start.isoformat(),
                    timeMax=end.isoformat(),
                    # maxResults=10,
                    singleEvents=True,
                    privateExtendedProperty=["source=" + EXTENDED_PROPERTY_SOURCE],
                    orderBy="startTime",
                )
                .execute()
            )
            events = events_result.get("items", [])
            logger.debug(
                "Retrieved %d events from calendar %s", len(events), self.calendar_id
            )
            return [_event_from_calendar_dict(event_dict) for event_dict in events]

        except HttpError as error:
            logger.exception("Error fetching events from Google Calendar: %s", error)
            return []

    def apply_changes(self, changes: ChangeSet):
        def create_event_body(
            event: LessonEvent, is_update: bool = False
        ) -> dict[str, object]:
            event_body: dict[str, object] = {
                "summary": event.summary,
                "start": {"dateTime": event.start.isoformat()},
                "end": {"dateTime": event.end.isoformat()},
                "description": event.description,
                "location": event.location,
            }

            if not is_update:
                event_body["reminders"] = {"useDefault": False}
                event_body["extendedProperties"] = {
                    "private": {"source": EXTENDED_PROPERTY_SOURCE}
                }

            return event_body

        # Add new events
        add_count = 0
        for event in changes.to_add:
            event_body = create_event_body(event)
            self.service.events().insert(
                calendarId=self.calendar_id, body=event_body
            ).execute()
            add_count += 1

        # Remove events
        remove_count = 0
        for event_to_remove in changes.to_remove:
            event_id = event_to_remove.id
            self.service.events().delete(
                calendarId=self.calendar_id, eventId=event_id
            ).execute()
            remove_count += 1

        # Update existing events
        update_count = 0
        for update_diff in changes.to_update:
            event_body = create_event_body(update_diff.new, is_update=True)
            self.service.events().patch(
                calendarId=self.calendar_id, eventId=update_diff.id, body=event_body
            ).execute()
            update_count += 1

        logger.debug(
            "Applied %d changes to calendar %s: add=%d update=%d remove=%d",
            add_count + update_count + remove_count,
            self.calendar_id,
            add_count,
            update_count,
            remove_count,
        )
