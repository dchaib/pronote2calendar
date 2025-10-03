from pronote2calendar.config_manager import read_config
from datetime import date, timedelta
from pronote2calendar.pronote_client import PronoteClient

def main():

    config = read_config()

    client = PronoteClient(config['pronote'])

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
