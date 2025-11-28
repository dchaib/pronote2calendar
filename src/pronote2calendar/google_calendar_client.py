import logging
from datetime import datetime
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build  # type: ignore
from googleapiclient.errors import HttpError  # type: ignore

from pronote2calendar.settings import GoogleCalendarSettings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
]
EXTENDED_PROPERTY_SOURCE = "pronote2calendar"


class GoogleCalendarClient:
    def __init__(self, config: GoogleCalendarSettings, credentials_file_path: str):
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file_path, scopes=SCOPES
        )
        self.service = build("calendar", "v3", credentials=credentials)
        self.calendar_id = config.calendar_id

    def get_events(self, start: datetime, end: datetime) -> list[dict[str, Any]]:
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
            return events

        except HttpError as error:
            logger.exception("Error fetching events from Google Calendar: %s", error)
            return []

    def apply_changes(self, changes: dict):

        def create_event_body(
            event: dict[str, Any], is_update: bool = False
        ) -> dict[str, Any]:
            event_body = {
                "summary": event.get("summary", ""),
                "start": {"dateTime": event["start"].isoformat()},
                "end": {"dateTime": event["end"].isoformat()},
                "description": event.get("description", ""),
            }

            if event.get("location"):
                event_body["location"] = event["location"]

            if not is_update:
                event_body["reminders"] = {"useDefault": False}
                event_body["extendedProperties"] = {
                    "private": {"source": EXTENDED_PROPERTY_SOURCE}
                }

            return event_body

        # Add new events
        add_count = 0
        for event in changes.get("add", []):
            event_body = create_event_body(event)
            self.service.events().insert(
                calendarId=self.calendar_id, body=event_body
            ).execute()
            add_count += 1

        # Remove events
        remove_count = 0
        for event in changes.get("remove", []):
            event_id = event["id"]
            self.service.events().delete(
                calendarId=self.calendar_id, eventId=event_id
            ).execute()
            remove_count += 1

        # Update existing events
        update_count = 0
        for event in changes.get("update", []):
            event_body = create_event_body(event, is_update=True)
            event_id = event["id"]
            self.service.events().patch(
                calendarId=self.calendar_id, eventId=event_id, body=event_body
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
