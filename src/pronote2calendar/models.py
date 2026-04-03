from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class CalendarEvent:
    id: str
    start: datetime
    end: datetime
    summary: str | None = None
    description: str | None = None
    location: str | None = None


@dataclass
class LessonEvent:
    start: datetime
    end: datetime
    summary: str | None
    description: str | None
    location: str | None


@dataclass
class UpdateDiff:
    id: str
    old: CalendarEvent
    new: LessonEvent
    changes: dict[str, tuple[Any, Any]]


@dataclass
class ChangeSet:
    to_add: list[LessonEvent]
    to_update: list[UpdateDiff]
    to_remove: list[CalendarEvent]
