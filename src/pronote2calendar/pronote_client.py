import pronotepy
from datetime import date

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
        return self.client.lessons(start, end)
