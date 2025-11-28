import logging
from datetime import time
from pathlib import Path

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

logger = logging.getLogger(__name__)


class PronoteSettings(BaseSettings):
    connection_type: str = Field(default="token")
    account_type: str = Field(default="child")
    child: str = Field(default="")


class GoogleCalendarSettings(BaseSettings):
    calendar_id: str


class TimeAdjustment(BaseSettings):
    weekdays: list[int]
    start_times: dict[time, time] = Field(default_factory=dict)
    end_times: dict[time, time] = Field(default_factory=dict)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(yaml_file=Path("config.yaml"))

    pronote: PronoteSettings
    google_calendar: GoogleCalendarSettings
    num_weeks_to_sync: int = Field(default=3)
    log_level: str = Field(default="INFO")
    time_adjustments: list[TimeAdjustment] = Field(default_factory=list)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (YamlConfigSettingsSource(settings_cls),)
