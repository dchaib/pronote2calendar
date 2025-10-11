import datetime
from typing import Any
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
]
EXTENDED_PROPERTY_SOURCE="pronote2calendar"

class GoogleCalendarClient:
    def __init__(self, config, credentials_file_path):
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file_path, scopes=SCOPES)
        self.service = build("calendar", "v3", credentials=credentials)
        self.calendar_id = config["calendar_id"]

    def get_events(self, start: datetime, end: datetime):
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
            return events

        except HttpError as error:
            print(f"An error occurred: {error}")

    def apply_changes(self, changes: dict):
    
        def create_event_body(event: dict[str, Any], is_update: bool = False) -> dict[str, Any]:
            event_body = {
                'summary': event.get('summary', ''),
                'start': {
                    'dateTime': event['start'].isoformat()
                },
                'end': {
                    'dateTime': event['end'].isoformat()
                },
                'description': event.get('description', '')
            }

            if event.get('location'):
                event_body['location'] = event['location']

            if not is_update:
                event_body['reminders'] = {'useDefault': False}
                event_body['extendedProperties'] = {'private': {'source': EXTENDED_PROPERTY_SOURCE }}

            return event_body

        batch = self.service.new_batch_http_request()

        # Add new events
        for event in changes.get('add', []):
            event_body = create_event_body(event)
            batch.add(self.service.events().insert(calendarId=self.calendar_id, body=event_body))

        # Remove events
        for event in changes.get('remove', []):
            event_id = event['id']
            batch.add(self.service.events().delete(calendarId=self.calendar_id, eventId=event_id))

        # Update existing events
        for event in changes.get('update', []):
            event_body = create_event_body(event, is_update=True)
            event_id = event['id']
            batch.add(self.service.events().patch(calendarId=self.calendar_id, eventId=event_id, body=event_body))
            
        batch.execute()
