from datetime import datetime

from src.domain.models import BaseModel, UpdateTask, UpdateTodo
from src.domain.types import (
    NonNegativeInt,
    PageLimitField,
    PositiveInt,
    TaskPriority,
    TaskStatus,
    TodoStatus,
)


class LimitOffsetQuery(BaseModel):
    limit: PageLimitField
    offset: NonNegativeInt = 0


class TasksFilter(BaseModel):
    task_id: list[PositiveInt] | None = None
    todo_id: list[PositiveInt]
    brief: list[str] | None = None
    category: list[str] | None = None
    status: list[TaskStatus] | None = None
    priority: list[TaskPriority] | None = None
    due: list[datetime] | None = None
    created_at: list[datetime] | None = None
    updated_at: list[datetime] | None = None


class GetTasksQuery(LimitOffsetQuery):
    filters: TasksFilter | None = None


class GetTaskQuery(BaseModel):
    task_id: PositiveInt


class UpdateTaskQuery(BaseModel):
    task_id: PositiveInt
    payload: UpdateTask


class DeleteTaskQuery(BaseModel):
    task_id: PositiveInt


class TodosFilter(BaseModel):
    todo_id: list[PositiveInt] | None = None
    owner: list[str] | None = None
    status: list[TodoStatus] | None = None
    created_at: list[datetime] | None = None
    updated_at: list[datetime] | None = None


class GetTodosQuery(LimitOffsetQuery):
    filters: TodosFilter | None = None


class GetTodoQuery(BaseModel):
    todo_id: PositiveInt
    prefetch_tasks: NonNegativeInt = 0


class UpdateTodoQuery(BaseModel):
    todo_id: PositiveInt
    payload: UpdateTodo


class DeleteTodoQuery(BaseModel):
    todo_id: PositiveInt
