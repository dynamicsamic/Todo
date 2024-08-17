from datetime import datetime
from typing import Any

from pydantic import BaseModel as _BaseModel
from pydantic import ConfigDict, Field, model_validator

from src.utils import datetime_with_delta

from .types import (
    PositiveInt,
    TaskPriority,
    TaskStatus,
    TodoStatus,
    TZDatetime,
)


class NonEmptyUpdateMixin:
    @model_validator(mode="before")
    @classmethod
    def check_at_least_one_non_empty_field(cls, data: dict[str, Any]) -> Any:
        if all(val is None for val in data.values()):
            raise ValueError(
                "At least one field must contain a not None value"
            )
        return data


class BaseModel(_BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class Task(BaseModel):
    task_id: PositiveInt
    brief: str
    todo_id: PositiveInt
    contents: str | None = None
    status: TaskStatus
    priority: TaskPriority
    category: str
    due: datetime
    created_at: datetime
    updated_at: datetime


class CreateTask(BaseModel):
    brief: str
    todo_id: PositiveInt
    contents: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.LOW
    category: str
    due: TZDatetime | None = Field(
        default_factory=datetime_with_delta({"days": 1})
    )


class UpdateTask(BaseModel, NonEmptyUpdateMixin):
    brief: str | None = None
    todo_id: PositiveInt | None = None
    contents: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    category: str | None = None
    due: TZDatetime | None = None
    created_at: TZDatetime | None = None
    updated_at: TZDatetime | None = None


class Todo(BaseModel):
    todo_id: PositiveInt
    owner: str
    status: TodoStatus
    created_at: datetime
    updated_at: datetime
    tasks: list[Task] | None = []


class CreateTodo(BaseModel):
    owner: str
    status: TodoStatus | None = TodoStatus.ACTIVE


class UpdateTodo(BaseModel, NonEmptyUpdateMixin):
    owner: str | None = None
    status: TodoStatus | None = None
    created_at: TZDatetime | None = None
    updated_at: TZDatetime | None = None
