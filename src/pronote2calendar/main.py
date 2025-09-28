import os
from dotenv import load_dotenv
from datetime import date, timedelta
from pronote2calendar.pronote_client import PronoteClient

def main():
    load_dotenv()

    url = os.environ["PRONOTE_URL"]
    username = os.environ["PRONOTE_USERNAME"]
    password = os.environ["PRONOTE_PASSWORD"]

    client = PronoteClient(url, username, password)

    if not client.is_logged_in():
        print("Login failed!")
        return

    start = date.today()
    end = start + timedelta(days=10)

    timetable = client.get_lessons(start, end)

    for lesson in timetable:
        print(f"{lesson.start} - {lesson.end} | {lesson.subject.name} | {lesson.classroom}")

if __name__ == "__main__":
    main()
