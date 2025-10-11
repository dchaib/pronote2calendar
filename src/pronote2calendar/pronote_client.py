import pronotepy
from datetime import date
from itertools import groupby

from pronote2calendar.config_manager import update_pronote_password

class PronoteClient:
    def __init__(self, config):
        self.client = self.get_pronote_client(config)
    
    def get_pronote_client(self, config):
        if config["connection_type"] == "token":
            client = self.get_client_from_token_login(config)
        else:
            client = self.get_client_from_username_password(config)

        if isinstance(client, pronotepy.ParentClient):
            client.set_child(config["child"])

        return client
    
    def get_client_from_token_login(self, config) -> pronotepy.ClientBase:
        client = (
            pronotepy.ParentClient
            if config["account_type"] == "parent"
            else pronotepy.Client
        ).token_login(
            pronote_url=config["url"],
            username=config["username"],
            password=config["password"],
            uuid=config["uuid"],
            client_identifier=config["client_identifier"]
        )

        update_pronote_password(client.password)

        return client
    
    def get_client_from_username_password(self, config) -> pronotepy.ClientBase:
        client = (
            pronotepy.ParentClient
            if config["account_type"] == "parent"
            else pronotepy.Client
        )(
            pronote_url=config["url"],
            username=config["username"],
            password=config["password"]
        )
        return client

    def is_logged_in(self) -> bool:
        return self.client.logged_in

    def get_lessons(self, start: date, end: date):
        lessons = self.client.lessons(start, end)
        return self.sort_and_filter_lessons(lessons)

    def sort_and_filter_lessons(self, lessons: list[pronotepy.Lesson]) -> list[pronotepy.Lesson]:
        lessons.sort(key=lambda x: (x.start, -x.num))
        
        filtered_lessons = []
        for _, group in groupby(lessons, key=lambda x: x.start):
            filtered_lessons.append(max(group, key=lambda x: x.num))
        
        return filtered_lessons
