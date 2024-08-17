from pydantic import Field
from pydantic.json_schema import SkipJsonSchema

from src.domain.models import BaseModel, CreateTask, Task, Todo
from src.domain.types import (
    DateTimeList,
    NonNegativeInt,
    PageLimitField,
    PositiveInt,
    PositiveIntList,
    StringList,
    TaskPriorityList,
    TaskStatusList,
    TodoStatusList,
)


class CommonQueryArgs(BaseModel):
    limit: PageLimitField
    offset: NonNegativeInt | None = 0
    created_at: DateTimeList | None = None
    updated_at: DateTimeList | None = None

    def to_service_query_schema(self):
        filters = self.model_dump(exclude_none=True)
        limit = filters.pop("limit")
        offset = filters.pop("offset")

        return {"limit": limit, "offset": offset, "filters": filters}


class ListTodosQueryArgs(CommonQueryArgs):
    owner: StringList | None = None
    status: TodoStatusList | None = None
    todo_id: PositiveIntList | None = None


class ListTasksQueryArgs(CommonQueryArgs):
    task_id: PositiveIntList | None = None
    brief: StringList | None = None
    category: StringList | None = None
    status: TaskStatusList | None = None
    priority: TaskPriorityList | None = None
    due: DateTimeList | None = None


class TaskList(BaseModel):
    tasks: list[Task] | None = []


class CreateTaskNoTodoId(CreateTask):
    todo_id: SkipJsonSchema[PositiveInt] = Field(default=None, exclude=True)


class TodoList(BaseModel):
    todos: list[Todo] | None = []


class GetTodoQueryArgs(BaseModel):
    prefetch_tasks: NonNegativeInt | None = 0
