import json
from datetime import date, timedelta
from pronote2calendar.pronote_client import PronoteClient

def main():

    with open('config.json', 'r') as file:
        config = json.load(file)

    pronote_config = config['pronote']

    client = PronoteClient(pronote_config)

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
