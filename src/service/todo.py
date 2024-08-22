import logging
from typing import Any

from src.domain.models import CreateTodo, Todo, UpdateTodo

from ._base import Service
from .schemas import (
    DeleteTodoQuery,
    GetTodoQuery,
    GetTodosQuery,
    UpdateTodoQuery,
)
from .validation import validate_input_output, validate_query

logger = logging.getLogger(__name__)


class TodoService(Service):
    @validate_input_output(input_model=GetTodoQuery, output_model=Todo)
    async def get_one(
        self,
        *,
        todo_id: int,
        prefetch_tasks: int = 0,
    ) -> Todo | None:
        return await super().get_one(pk=todo_id, prefetch_tasks=prefetch_tasks)

    @validate_input_output(
        input_model=GetTodosQuery, output_model=Todo, return_list=True
    )
    async def get_many(
        self,
        *,
        limit: int = 10,
        offset: int = 0,
        filters: dict[str, list[Any]] | None = None,
    ) -> list[Todo]:
        return await super().get_many(limit=limit, offset=offset, filters=filters)

    @validate_input_output(input_model=CreateTodo, output_model=Todo)
    async def create(self, **payload: Any) -> Todo | None:
        return await super().create(**payload)

    @validate_input_output(input_model=UpdateTodoQuery, output_model=Todo)
    async def update(self, *, todo_id: int, payload: UpdateTodo) -> Todo | None:
        return await super().update(pk=todo_id, payload=payload)

    @validate_query(DeleteTodoQuery)
    async def delete(self, *, todo_id: int) -> bool:
        return await super().delete(pk=todo_id)
