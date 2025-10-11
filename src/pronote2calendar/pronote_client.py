import json
import pronotepy
from datetime import date
from itertools import groupby

class PronoteClient:
    def __init__(self, config, credentials_file_path):
        self.credentials_file_path = credentials_file_path
        self.client = self.get_pronote_client(config, credentials_file_path)
    
    def get_pronote_client(self, config, credentials_file_path):
        with open(credentials_file_path, 'r') as file:
            credentials = json.load(file)
        
        if config["connection_type"] == "token":
            client = self.get_client_from_token_login(config, credentials)
        else:
            client = self.get_client_from_username_password(config, credentials)

        if isinstance(client, pronotepy.ParentClient):
            client.set_child(config["child"])

        return client
    
    def get_client_from_token_login(self, config, credentials) -> pronotepy.ClientBase:
        client = (
            pronotepy.ParentClient
            if config["account_type"] == "parent"
            else pronotepy.Client
        ).token_login(
            pronote_url=credentials["url"],
            username=credentials["username"],
            password=credentials["password"],
            uuid=credentials["uuid"],
            client_identifier=credentials["client_identifier"]
        )

        self.update_pronote_password(client.password)

        return client
    
    def get_client_from_username_password(self, config, credentials) -> pronotepy.ClientBase:
        client = (
            pronotepy.ParentClient
            if config["account_type"] == "parent"
            else pronotepy.Client
        )(
            pronote_url=credentials["url"],
            username=credentials["username"],
            password=credentials["password"]
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

    def update_pronote_password(self, new_password: str):
        with open(self.credentials_file_path, 'r') as file:
            credentials = json.load(file)

        credentials['password'] = new_password

        with open(self.credentials_file_path, 'w') as file:
            json.dump(credentials, file, indent=4)
