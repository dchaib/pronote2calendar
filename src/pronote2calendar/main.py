from datetime import date, datetime, timedelta
from pronote2calendar import change_detection
from pronote2calendar.config_manager import read_config
from pronote2calendar.pronote_client import PronoteClient
from pronote2calendar.google_calendar_client import GoogleCalendarClient


def main():
    config = read_config()
    start = datetime.combine(date.today(), datetime.min.time()).astimezone()
    end = start + timedelta(days=2)

    print(f"Updating lessons from {start} to {end}...")

    pronote = PronoteClient(config["pronote"], "credentials-pronote.json")

    if not pronote.is_logged_in():
        print("Login failed!")
        return

    lessons = pronote.get_lessons(start, end)

    calendar = GoogleCalendarClient(config["google_calendar"], "credentials-google.json")
    events = calendar.get_events(start, end)

    changes = change_detection.get_changes(lessons, events)

    for action, items in changes.items():
        print(f"\n{action.upper()}:")
        for item in items:
            print(item)

    calendar.apply_changes(changes)


if __name__ == "__main__":
    main()
