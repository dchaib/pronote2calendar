import pronotepy
from datetime import date

class PronoteClient:
    def __init__(self, config):
        self.client = self.get_pronote_client(config)
    
    def get_pronote_client(self, config):
        client = (
            pronotepy.ParentClient
            if config["account_type"] == "parent"
            else pronotepy.Client
        )(
            pronote_url=config["url"],
            username=config["username"],
            password=config["password"]
        )

        if isinstance(client, pronotepy.ParentClient):
            client.set_child(config["child"])

        return client

    def is_logged_in(self) -> bool:
        return self.client.logged_in

    def get_lessons(self, start: date, end: date):
        return self.client.lessons(start, end)
