from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any

from pydantic import AfterValidator, BeforeValidator, Field

from src.settings import settings


class TodoStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class TaskStatus(StrEnum):
    PENDING = "pending"
    COMPLETE = "complete"
    POSTPONED = "postponed"


class TaskPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


def _to_list(value: Any | list[Any]) -> list[Any]:
    """Insure the result is returned in a list."""
    if isinstance(value, list):
        return value
    return [value]


def add_timezone(d: datetime) -> datetime:
    return d.astimezone(settings.TZ)


TZDatetime = Annotated[datetime, AfterValidator(add_timezone)]
PositiveInt = Annotated[int, Field(gt=0)]
NonNegativeInt = Annotated[int, Field(gt=-1)]
PageLimitField = Annotated[
    int,
    Field(default=settings.DEFAULT_PAGE_LIMIT, gt=0, lt=settings.MAX_PAGE_LIMIT),
]
StringList = Annotated[list[str], BeforeValidator(_to_list)]
TodoStatusList = Annotated[list[TodoStatus], BeforeValidator(_to_list)]
PositiveIntList = Annotated[list[PositiveInt], BeforeValidator(_to_list)]
DateTimeList = Annotated[list[datetime], BeforeValidator(_to_list)]
TaskStatusList = Annotated[list[TaskStatus], BeforeValidator(_to_list)]
TaskPriorityList = Annotated[list[TaskPriority], BeforeValidator(_to_list)]
