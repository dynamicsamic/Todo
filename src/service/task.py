import logging
from typing import Any

from src.domain.models import CreateTask, Task, UpdateTask

from ._base import Service
from .schemas import (
    DeleteTaskQuery,
    GetTaskQuery,
    GetTasksQuery,
    UpdateTaskQuery,
)
from .validation import validate_input_output, validate_query

logger = logging.getLogger(__name__)


class TaskService(Service):
    @validate_input_output(input_model=GetTaskQuery, output_model=Task)
    async def get_one(self, *, task_id: int) -> Task | None:
        return await super().get_one(pk=task_id)

    @validate_input_output(
        input_model=GetTasksQuery, output_model=Task, return_list=True
    )
    async def get_many(
        self,
        *,
        limit: int = 10,
        offset: int = 0,
        filters: dict[str, list[Any]] | None = None,
    ) -> list[Task]:
        return await super().get_many(limit=limit, offset=offset, filters=filters)

    @validate_input_output(input_model=CreateTask, output_model=Task)
    async def create(self, **payload: Any) -> Task | None:
        return await super().create(**payload)

    @validate_input_output(input_model=UpdateTaskQuery, output_model=Task)
    async def update(self, *, task_id: int, payload: UpdateTask) -> Task | None:
        return await super().update(pk=task_id, payload=payload)

    @validate_query(DeleteTaskQuery)
    async def delete(self, *, task_id: int) -> bool:
        return await super().delete(pk=task_id)
