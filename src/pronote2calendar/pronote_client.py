import pronotepy
from datetime import date

class PronoteClient:
    def __init__(self, url: str, username: str, password: str):
        self.client = pronotepy.Client(url, username=username, password=password)

    def is_logged_in(self) -> bool:
        return self.client.logged_in

    def get_lessons(self, start: date, end: date):
        return self.client.lessons(start, end)
