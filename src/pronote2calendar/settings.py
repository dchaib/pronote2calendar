from datetime import time
from pathlib import Path
from typing import Annotated, Any, Literal, Self

from pydantic import BeforeValidator, EmailStr, Field, model_validator
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
    calendar_id: EmailStr = Field(description="Email address of the Google Calendar")


class SyncSettings(BaseSettings):
    weeks: int = Field(default=3, ge=1)


class TimeAdjustmentRule(BaseSettings):
    weekdays: list[WeekdayNum]
    start_times: dict[FlexibleTime, FlexibleTime] = Field(default_factory=dict)
    end_times: dict[FlexibleTime, FlexibleTime] = Field(default_factory=dict)


class AjustmentsSettings(BaseSettings):
    time: list[TimeAdjustmentRule] = Field(default_factory=list)
    subject: dict[str, str] = Field(default_factory=dict)


class EventsTemplates(BaseSettings):
    summary: str = Field(default="{{ subject }}")
    description: str = Field(default="{{ teacher_name }}")
    location: str = Field(default="{{ classroom }}")


class EventsSettings(BaseSettings):
    templates: EventsTemplates = Field(default_factory=EventsTemplates)


class NotificationsTemplates(BaseSettings):
    # Jinja2 templates; context will include 'adds','updates','removes','changes' lists
    title: str = Field(default="Pronote2Calendar sync")
    body: str = Field(
        default="""
Changes detected during synchronization:\n
{% for ev in adds %}- Added: {{ ev.summary }} ({{ ev.start }} - {{ ev.end }})\n  {{ ev.location }} {{ ev.description }}\n{% endfor %}
{% for ev in updates %}- Updated: {{ ev.summary }} ({{ ev.start }} - {{ ev.end }})\n  {{ ev.location }} {{ ev.description }}\n{% endfor %}
{% for ev in removes %}- Removed: {{ ev.summary }} ({{ ev.start }} - {{ ev.end }})\n  {{ ev.location }} {{ ev.description }}\n{% endfor %}
"""
    )


class NotificationsSettings(BaseSettings):
    enabled: bool = Field(
        default=False,
        description="Whether notifications are enabled (default false)",
    )
    destinations: list[str] = Field(
        default_factory=list,
        description="List of notification service URLs or config paths",
    )
    max_delay_days: int = Field(
        default=3,
        ge=0,
        description="Only notify about changes with start <= now + this many days",
    )
    templates: NotificationsTemplates = Field(default_factory=NotificationsTemplates)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(yaml_file=Path("config.yaml"))

    pronote: PronoteSettings = Field(default_factory=PronoteSettings)
    google_calendar: GoogleCalendarSettings
    sync: SyncSettings = Field(default_factory=SyncSettings)
    log_level: str = Field(default="INFO")
    adjustments: AjustmentsSettings = Field(default_factory=AjustmentsSettings)
    events: EventsSettings = Field(default_factory=EventsSettings)
    notifications: NotificationsSettings = Field(default_factory=NotificationsSettings)

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
