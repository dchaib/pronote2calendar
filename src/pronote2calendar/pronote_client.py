import json
import logging
from datetime import date
from itertools import groupby
from zoneinfo import ZoneInfo

import pronotepy

logger = logging.getLogger(__name__)


class PronoteClient:
    def __init__(self, config, credentials_file_path, timezone="Europe/Paris"):
        self.credentials_file_path = credentials_file_path
        self.timezone = ZoneInfo(timezone)
        self.client = self.get_pronote_client(config, credentials_file_path)
        logger.debug(
            "Pronote client initialized; logged_in=%s",
            getattr(self.client, "logged_in", False),
        )

    def get_pronote_client(self, config, credentials_file_path) -> pronotepy.ClientBase:
        with open(credentials_file_path, "r") as file:
            credentials = json.load(file)

        if config["connection_type"] == "token":
            client = self.get_client_from_token_login(config, credentials)
        else:
            client = self.get_client_from_username_password(config, credentials)

        if isinstance(client, pronotepy.ParentClient):
            client.set_child(config["child"])

        logger.debug(
            "Pronote client created for account_type=%s connection_type=%s",
            config.get("account_type"),
            config.get("connection_type"),
        )
        return client

    def get_client_from_token_login(self, config, credentials) -> pronotepy.ClientBase:
        client = (
            pronotepy.ParentClient
            if config["account_type"] == "parent"
            else pronotepy.Client
        ).token_login(**credentials)

        self.update_credentials(client.export_credentials())

        return client

    def get_client_from_username_password(
        self, config, credentials
    ) -> pronotepy.ClientBase:
        client = (
            pronotepy.ParentClient
            if config["account_type"] == "parent"
            else pronotepy.Client
        )(**credentials)
        return client

    def is_logged_in(self) -> bool:
        logged_in = self.client.logged_in
        logger.debug("Pronote is_logged_in check: %s", logged_in)
        return logged_in

    def get_lessons(self, start: date, end: date) -> list[pronotepy.Lesson]:
        logger.debug("Fetching lessons from %s to %s", start, end)
        lessons = self.client.lessons(start, end)
        result = self.sort_and_filter_lessons(lessons)
        result = self._convert_lessons_to_aware(result)
        logger.debug("Raw lessons fetched: %d", len(lessons))
        logger.debug("Fetched %d lessons (after filter)", len(result))
        return result

    def sort_and_filter_lessons(
        self, lessons: list[pronotepy.Lesson]
    ) -> list[pronotepy.Lesson]:
        lessons.sort(key=lambda x: (x.start, -x.num))

        filtered_lessons = []
        for _, group in groupby(lessons, key=lambda x: x.start):
            filtered_lessons.append(max(group, key=lambda x: x.num))

        filtered_lessons = [
            lesson for lesson in filtered_lessons if not lesson.canceled
        ]

        return filtered_lessons

    def update_credentials(self, credentials: dict):
        with open(self.credentials_file_path, "w") as file:
            json.dump(credentials, file, indent=4)
        logger.debug("Pronote credentials updated in %s", self.credentials_file_path)

    def _convert_to_aware(self, naive_datetime):
        if naive_datetime.tzinfo is None:
            return naive_datetime.replace(tzinfo=self.timezone)
        return naive_datetime

    def _convert_lessons_to_aware(self, lessons):
        for lesson in lessons:
            lesson.start = self._convert_to_aware(lesson.start)
            lesson.end = self._convert_to_aware(lesson.end)
        return lessons
