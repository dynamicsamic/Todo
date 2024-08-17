import pytest
from pydantic import ValidationError

from src.domain.types import TaskPriority, TaskStatus, TodoStatus
from src.service.schemas import (
    DeleteTaskQuery,
    DeleteTodoQuery,
    GetTaskQuery,
    GetTasksQuery,
    GetTodoQuery,
    GetTodosQuery,
    UpdateTaskQuery,
    UpdateTodoQuery,
)
from src.settings import settings
from src.utils import now as now_

DEFAULT_LIMIT = settings.DEFAULT_PAGE_LIMIT
now = now_()


class TestTodoSchemas:
    def test_get_todos_query_without_args(self):
        query = GetTodosQuery()

        assert query.limit == DEFAULT_LIMIT
        assert query.offset == 0
        assert query.filters is None

    def test_get_todos_query_with_limit_offset(self):
        limit, offset = 14, 22
        query = GetTodosQuery(limit=limit, offset=offset)

        assert query.limit == limit
        assert query.offset == offset
        assert query.filters is None

    def test_get_todos_query_with_some_filters(self):
        filters = {
            "owner": ["bob", "alice", "helen"],
            "status": [TodoStatus.ACTIVE, TodoStatus.INACTIVE],
        }
        query = GetTodosQuery(filters=filters)

        assert query.model_dump(exclude_none=True)["filters"] == filters

    def test_get_todos_query_with_all_args_and_filters(self):
        limit, offset = 14, 22
        filters = {
            "todo_id": [1, 324, 44],
            "owner": ["bob", "alice", "helen"],
            "status": [TodoStatus.ACTIVE, TodoStatus.INACTIVE],
            "created_at": [now, now],
            "updated_at": [now],
        }
        query = GetTodosQuery(limit=limit, offset=offset, filters=filters)

        query = query.model_dump(exclude_none=True)
        assert query["limit"] == limit
        assert query["offset"] == offset
        assert query["filters"] == filters

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_get_todos_query_negative_limit(self):
        GetTodosQuery(limit=-1)

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_get_todos_query_negative_offset(self):
        GetTodosQuery(offset=-1)

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_get_todos_query_extra_arg(self):
        GetTodosQuery(extra="extra")

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_get_todos_query_non_list_arg_type_filter(self):
        filters = {
            "owner": ["bob", "alice", "helen"],
            "todo_id": 1,
            "status": [TodoStatus.ACTIVE, TodoStatus.INACTIVE],
        }
        GetTodosQuery(filters=filters)

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_get_todos_query_invalid_status_filter(self):
        filters = {
            "todo_id": [1],
            "status": [TodoStatus.ACTIVE, "Invalid"],
        }
        GetTodosQuery(filters=filters)

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_get_todos_query_extra_arg_filter(self):
        filters = {
            "owner": ["bob", "alice", "helen"],
            "status": [TodoStatus.ACTIVE, TodoStatus.INACTIVE],
            "extra": ["extra1", "extra2"],
        }
        GetTodosQuery(filters=filters)

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_get_todos_query_negative_id_filter(self):
        filters = {
            "owner": ["bob", "alice", "helen"],
            "todo_id": [1, 2, 3, 4, -34],
            "status": [TodoStatus.ACTIVE, TodoStatus.INACTIVE],
        }
        GetTodosQuery(filters=filters)

    def test_get_todo_query_valid_id(self):
        todo_id = 1
        query = GetTodoQuery(todo_id=todo_id)

        assert query.todo_id == todo_id
        assert query.prefetch_tasks == 0

    def test_get_todo_query_valid_prefetch(self):
        todo_id, prefetch = 5, 10
        query = GetTodoQuery(todo_id=todo_id, prefetch_tasks=prefetch)

        assert query.todo_id == todo_id
        assert query.prefetch_tasks == prefetch

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_get_todo_query_without_args(self):
        GetTodoQuery()

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_get_todo_query_not_positive_id(self):
        GetTodoQuery(todo_id=0)

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_get_todo_query_negative_prefetch(self):
        GetTodoQuery(todo_id=1, prefetch_tasks=-1)

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_get_todo_query_extra_arg(self):
        GetTodoQuery(todo_id=1, extra="extra")

    def test_update_todo_query_valid_partial_payload(self):
        todo_id, payload = 1, {"owner": "new_owner"}

        query = UpdateTodoQuery(todo_id=todo_id, payload=payload)
        query = query.model_dump(exclude_none=True)
        assert query["todo_id"] == todo_id
        assert query["payload"] == payload

    def test_update_todo_query_valid_complete_payload(self):
        todo_id = 1
        payload = {
            "owner": "new_owner",
            "status": TodoStatus.ACTIVE,
            "created_at": now,
            "updated_at": now,
        }
        query = UpdateTodoQuery(todo_id=todo_id, payload=payload)
        query = query.model_dump(exclude_none=True)
        assert query["todo_id"] == todo_id
        assert query["payload"] == payload

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_update_todo_query_negative_todo_id(self):
        UpdateTodoQuery(todo_id=-1, payload={"owner": "new_owner"})

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_update_todo_query_invalid_payload(self):
        UpdateTodoQuery(todo_id=1, payload={"owner": 1123})

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_update_todo_query_empty_payload(self):
        UpdateTodoQuery(todo_id=1, payload={})

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_update_todo_query_extra_arg(self):
        UpdateTodoQuery(todo_id=1, payload={"extra": "extra"})

    def test_delete_todo_query_valid_id(self):
        todo_id = 10
        assert DeleteTodoQuery(todo_id=todo_id).todo_id == todo_id

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_delete_todo_query_negative_id(self):
        assert DeleteTodoQuery(todo_id=-1)

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_delete_todo_query_without_args(self):
        DeleteTodoQuery()

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_delete_todo_query_extra_arg(self):
        DeleteTodoQuery(todo_id=1, extra="extra")


"""
getTasksQuery (limit+offset+filters)
getTaskQuery (task_id)
UpdateTaskQuery (task_id + payload)
deleteTaskQuery (task_id)
"""


class TestTaskSchemas:

    def test_get_tasks_query_some_filters(self):
        filters = {
            "task_id": [1, 2, 3],
            "todo_id": [1],
            "brief": ["brief1"],
            "priority": [TaskPriority.HIGH],
            "category": ["category2", "category1", "category4"],
            "due": [now],
        }
        query = GetTasksQuery(filters=filters)
        assert query.model_dump(exclude_unset=True)["filters"] == filters

    def test_get_tasks_query_all_filters(self):
        filters = {
            "task_id": [1, 2, 3],
            "todo_id": [1, 3],
            "brief": ["brief1"],
            "status": [TaskStatus.COMPLETE, TaskStatus.PENDING],
            "priority": [TaskPriority.HIGH],
            "category": ["category2", "category1", "category4"],
            "due": [now],
            "created_at": [now, now],
            "updated_at": [now],
        }
        query = GetTasksQuery(filters=filters)
        assert query.model_dump(exclude_unset=True)["filters"] == filters

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_get_tasks_query_no_filters(self):
        # filters must contain `todo_id` to perform todo-specific search.
        GetTasksQuery(filters={})

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_get_tasks_query_extra_arg_filters(self):
        filters = {
            "task_id": [1, 2, 3],
            "todo_id": [1],
            "brief": ["brief1"],
            "priority": [TaskPriority.HIGH],
            "extra": ["extra1", "extra2"],
        }
        GetTasksQuery(filters=filters)

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_get_tasks_query_non_list_arg_type_filters(self):
        filters = {
            "task_id": [1, 2, 3],
            "todo_id": [1],
            "brief": "brief1",
            "priority": [TaskPriority.HIGH],
        }
        GetTasksQuery(filters=filters)

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_get_tasks_query_negative_id_filter(self):
        filters = {
            "task_id": [1, 2, -33],
            "todo_id": [1],
            "brief": ["brief1"],
            "priority": [TaskPriority.HIGH],
        }
        GetTasksQuery(filters=filters)

    def test_get_task_query_valid_id(self):
        task_id = 1
        assert GetTaskQuery(task_id=task_id).task_id == task_id

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_get_task_query_without_args(self):
        GetTaskQuery()

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_get_task_query_not_positive_id(self):
        GetTaskQuery(task_id=0)

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_get_task_query_extra_arg(self):
        GetTaskQuery(task_id=1, extra="extra")

    def test_update_task_query_valid_partial_payload(self):
        task_id, payload = 1, {"brief": "new_breif"}

        query = UpdateTaskQuery(task_id=task_id, payload=payload)
        query = query.model_dump(exclude_none=True)
        assert query["task_id"] == task_id
        assert query["payload"] == payload

    def test_update_task_query_valid_complete_payload(self):
        task_id = 1
        payload = {
            "todo_id": 3,
            "brief": "brief1",
            "status": TaskStatus.COMPLETE,
            "priority": TaskPriority.HIGH,
            "category": "category2",
            "due": now,
            "created_at": now,
            "updated_at": now,
        }
        query = UpdateTaskQuery(task_id=task_id, payload=payload)
        query = query.model_dump(exclude_none=True)
        assert query["task_id"] == task_id
        assert query["payload"] == payload

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_update_task_query_negative_task_id(self):
        UpdateTaskQuery(task_id=-1, payload={"brief": "new_brief"})

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_update_task_query_invalid_payload(self):
        UpdateTaskQuery(task_id=1, payload={"brief": 1123})

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_update_task_query_empty_payload(self):
        UpdateTaskQuery(task_id=1, payload={})

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_update_task_query_extra_arg(self):
        UpdateTaskQuery(task_id=1, payload={"extra": "extra"})

    def test_delete_task_query_valid_id(self):
        task_id = 10
        assert DeleteTaskQuery(task_id=task_id).task_id == task_id

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_delete_task_query_negative_id(self):
        assert DeleteTaskQuery(task_id=-1)

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_delete_task_query_without_args(self):
        DeleteTaskQuery()

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_delete_task_query_extra_arg(self):
        DeleteTaskQuery(task_id=1, extra="extra")
