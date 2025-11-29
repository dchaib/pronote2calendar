from datetime import time
from pathlib import Path
from typing import Annotated, Any, Literal, Self

from pydantic import BeforeValidator, Field, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)


def normalize_time(value: Any) -> Any:
    if (
        isinstance(value, str)
        and (parts := value.strip().split(":", 1))
        and parts[0].isdigit()
        and len(parts[0]) == 1
    ):
        return "0" + parts[0] + (":" + parts[1] if len(parts) > 1 else "")
    return value


WeekdayNum = Annotated[int, Field(ge=1, le=7, description="1=Monday, 7=Sunday")]
FlexibleTime = Annotated[time, BeforeValidator(normalize_time)]


class PronoteSettings(BaseSettings):
    connection_type: Literal["token", "password"] = Field(default="token")
    account_type: Literal["child", "parent"] = Field(default="child")
    child: str | None = Field(default=None)

    @model_validator(mode="after")
    def check_child_for_parent(self) -> Self:
        if self.account_type == "parent" and (not self.child or not self.child.strip()):
            raise ValueError("'child' is required when 'account_type' is 'parent'")
        return self


class GoogleCalendarSettings(BaseSettings):
    calendar_id: str


class SyncSettings(BaseSettings):
    weeks: int = Field(default=3, ge=1)


class TimeAdjustmentRule(BaseSettings):
    weekdays: list[WeekdayNum]
    start_times: dict[FlexibleTime, FlexibleTime] = Field(default_factory=dict)
    end_times: dict[FlexibleTime, FlexibleTime] = Field(default_factory=dict)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(yaml_file=Path("config.yaml"))

    pronote: PronoteSettings = Field(default_factory=PronoteSettings)
    google_calendar: GoogleCalendarSettings
    sync: SyncSettings = Field(default_factory=SyncSettings)
    log_level: str = Field(default="INFO")
    time_adjustments: list[TimeAdjustmentRule] = Field(default_factory=list)

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
