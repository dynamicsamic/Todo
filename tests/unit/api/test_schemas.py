import pytest
from pydantic import ValidationError

from src.domain.models import CreateTask, Task, Todo
from src.domain.types import TaskPriority, TaskStatus, TodoStatus
from src.service import schemas as service
from src.settings import settings
from src.utils import now as now_
from src.web.api.schemas import (
    CreateTaskNoTodoId,
    GetTodoQueryArgs,
    ListTasksQueryArgs,
    ListTodosQueryArgs,
    TaskList,
    TodoList,
)

DEFAULT_LIMIT = settings.DEFAULT_PAGE_LIMIT


now = now_()


class TestTodoAPISchemas:
    def test_list_todos_query_args_empty_request(self):
        query_args = ListTodosQueryArgs().model_dump(exclude_none=True)
        assert query_args == {"limit": DEFAULT_LIMIT, "offset": 0}

    def test_list_todos_query_args_with_valid_limit(self):
        limit = 15
        query_args = ListTodosQueryArgs(limit=limit).model_dump(
            exclude_none=True
        )
        assert query_args == {"limit": limit, "offset": 0}

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_list_todos_query_args_with_negative_limit(self):
        ListTodosQueryArgs(limit=-1)

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_list_todos_query_args_with_limit_to_high(self):
        ListTodosQueryArgs(limit=101)

    def test_list_todos_query_args_with_valid_offset(self):
        offset = 15
        query_args = ListTodosQueryArgs(offset=offset).model_dump(
            exclude_none=True
        )
        assert query_args == {"limit": DEFAULT_LIMIT, "offset": offset}

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_list_todos_query_args_with_negative_offset(self):
        ListTodosQueryArgs(offset=-1)

    def test_list_todos_query_args_with_valid_todo_id(self):
        todo_id = [1, 2, 3]
        query_args = ListTodosQueryArgs(todo_id=todo_id).model_dump(
            exclude_none=True
        )
        assert query_args == {
            "limit": DEFAULT_LIMIT,
            "offset": 0,
            "todo_id": todo_id,
        }

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_list_todos_query_args_with_invalid_todo_id(self):
        ListTodosQueryArgs(todo_id="hello world")

    def test_list_todos_query_args_with_valid_owner(self):
        owner = "bob"
        query_args = ListTodosQueryArgs(owner=owner).model_dump(
            exclude_none=True
        )
        assert query_args == {
            "limit": DEFAULT_LIMIT,
            "offset": 0,
            "owner": [owner],
        }

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_list_todos_query_args_with_invalid_owner(self):
        ListTodosQueryArgs(owner=14)

    def test_list_todos_query_args_with_valid_status(self):
        status = TodoStatus.ACTIVE
        query_args = ListTodosQueryArgs(status=status).model_dump(
            exclude_none=True
        )
        assert query_args == {
            "limit": DEFAULT_LIMIT,
            "offset": 0,
            "status": [status],
        }

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_list_todos_query_args_with_invalid_status(self):
        ListTodosQueryArgs(status="hello world")

    def test_list_todos_query_args_with_valid_created_at(self):
        created_at = now
        query_args = ListTodosQueryArgs(created_at=created_at).model_dump(
            exclude_none=True
        )
        assert query_args == {
            "limit": DEFAULT_LIMIT,
            "offset": 0,
            "created_at": [created_at],
        }

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_list_todos_query_args_with_invalid_created_at(self):
        ListTodosQueryArgs(created_at="hello world")

    def test_list_todos_query_args_all_attrs(self):
        args = {
            "limit": 12,
            "offset": 4,
            "todo_id": [1, 2, 4],
            "owner": "alice",
            "created_at": [now, now],
        }
        assert ListTodosQueryArgs.model_validate(args)

    def test_valid_list_todos_query_args_with_service_query_schema(self):
        args = {
            "limit": 12,
            "offset": 4,
            "todo_id": [1, 2, 4],
            "owner": "alice",
            "created_at": [now, now],
        }
        query_args = ListTodosQueryArgs.model_validate(args)
        service_schema = query_args.to_service_query_schema()
        assert service.GetTodosQuery.model_validate(service_schema)

    def test_empty_list_todos_query_args_with_service_query_schema(self):
        query_args = ListTodosQueryArgs()
        service_schema = query_args.to_service_query_schema()
        assert service.GetTodosQuery.model_validate(service_schema)

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_invalid_list_todos_query_args_with_service_query_schema(self):
        args = {
            "limit": "hello",
            "offset": 4,
            "todo_id": [1, 2, 4],
            "owner": "alice",
            "created_at": [now, now],
        }
        query_args = ListTodosQueryArgs.model_validate(args)
        service_schema = query_args.to_service_query_schema()
        service.GetTodosQuery.model_validate(service_schema)

    def test_get_todo_query_valid_prefetch(self):
        assert GetTodoQueryArgs(prefetch_tasks=10)

    def test_get_todo_query_empty_prefetch(self):
        assert GetTodoQueryArgs().prefetch_tasks == 0

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_get_todo_query_negative_prefetch(self):
        assert GetTodoQueryArgs(prefetch_tasks=-1)

    def test_todolist_valid_data_with_tasks(self):
        task = Task(
            task_id=1,
            brief="brief",
            todo_id=1,
            status=TaskStatus.COMPLETE,
            priority=TaskPriority.HIGH,
            category="category",
            due=now,
            created_at=now,
            updated_at=now,
        )
        todo = Todo(
            todo_id=1,
            owner="owner",
            status=TodoStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            tasks=[task for _ in range(3)],
        )
        assert TodoList(todos=[todo for _ in range(5)])

    def test_todolist_valid_data_without_tasks(self):
        todo = Todo(
            todo_id=1,
            owner="owner",
            status=TodoStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        assert TodoList(todos=[todo for _ in range(5)])

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_todolist_invalid_data(self):
        invalid_todo = {
            "todo_id": 1,
            "owner": "owner",
            "status": TodoStatus.ACTIVE,
            "extra": "extra",
        }
        assert TodoList(todos=[invalid_todo for _ in range(5)])


class TestTaskAPISchemas:
    def test_list_tasks_query_args_empty_request(self):
        query_args = ListTasksQueryArgs().model_dump(exclude_none=True)
        assert query_args == {"limit": DEFAULT_LIMIT, "offset": 0}

    def test_list_tasks_query_args_with_valid_limit(self):
        limit = 15
        query_args = ListTasksQueryArgs(limit=limit).model_dump(
            exclude_none=True
        )
        assert query_args == {"limit": limit, "offset": 0}

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_list_tasks_query_args_with_negative_limit(self):
        ListTasksQueryArgs(limit=-1)

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_list_tasks_query_args_with_limit_to_high(self):
        ListTasksQueryArgs(limit=101)

    def test_list_tasks_query_args_with_valid_offset(self):
        offset = 15
        query_args = ListTasksQueryArgs(offset=offset).model_dump(
            exclude_none=True
        )
        assert query_args == {"limit": DEFAULT_LIMIT, "offset": offset}

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_list_tasks_query_args_with_negative_offset(self):
        ListTasksQueryArgs(offset=-1)

    def test_list_tasks_query_args_with_valid_todo_id(self):
        task_id = [1, 2, 3]
        query_args = ListTasksQueryArgs(task_id=task_id).model_dump(
            exclude_none=True
        )
        assert query_args == {
            "limit": DEFAULT_LIMIT,
            "offset": 0,
            "task_id": task_id,
        }

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_list_tasks_query_args_with_invalid_task_id(self):
        ListTasksQueryArgs(task_id=0)

    def test_list_tasks_query_args_with_valid_brief(self):
        brief = "brief"
        query_args = ListTasksQueryArgs(brief=brief).model_dump(
            exclude_none=True
        )
        assert query_args == {
            "limit": DEFAULT_LIMIT,
            "offset": 0,
            "brief": [brief],
        }

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_list_tasks_query_args_with_invalid_brief(self):
        ListTasksQueryArgs(brief=14)

    def test_list_tasks_query_args_with_valid_status(self):
        status = TaskStatus.COMPLETE
        query_args = ListTasksQueryArgs(status=status).model_dump(
            exclude_none=True
        )
        assert query_args == {
            "limit": DEFAULT_LIMIT,
            "offset": 0,
            "status": [status],
        }

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_list_tasks_query_args_with_invalid_status(self):
        ListTasksQueryArgs(status="hello world")

    def test_list_tasks_query_args_with_valid_created_at(self):
        created_at = now
        query_args = ListTasksQueryArgs(created_at=created_at).model_dump(
            exclude_none=True
        )
        assert query_args == {
            "limit": DEFAULT_LIMIT,
            "offset": 0,
            "created_at": [created_at],
        }

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_list_tasks_query_args_with_invalid_created_at(self):
        ListTasksQueryArgs(created_at="hello world")

    def test_list_tasks_query_args_all_attrs(self):
        args = {
            "limit": 12,
            "offset": 4,
            "task_id": [1, 2, 4],
            "brief": ["brief"],
            "category": ["category1", "cateogry2"],
            "status": [
                TaskStatus.COMPLETE,
                TaskStatus.PENDING,
                TaskStatus.POSTPONED,
            ],
            "priority": [TaskPriority.HIGH],
            "due": [now],
            "created_at": [now, now],
            "updated_at": [now],
        }
        assert ListTasksQueryArgs.model_validate(args)

    def test_valid_list_tasks_query_to_service_schema(self):
        todo_id = 1
        args = {
            "limit": 12,
            "offset": 4,
            "task_id": [1, 2, 4],
            "brief": ["brief"],
            "category": ["category1", "cateogry2"],
            "status": [
                TaskStatus.COMPLETE,
                TaskStatus.PENDING,
                TaskStatus.POSTPONED,
            ],
            "priority": [TaskPriority.HIGH],
            "due": [now],
            "created_at": [now, now],
            "updated_at": [now],
        }
        query_args = ListTasksQueryArgs.model_validate(args)
        service_schema = query_args.to_service_query_schema()
        service_schema["filters"].update(todo_id=[todo_id])
        assert service.GetTasksQuery.model_validate(service_schema)

    def test_empty_list_tasks_query_to_service_schema(self):
        todo_id = 1
        query_args = ListTasksQueryArgs()
        service_schema = query_args.to_service_query_schema()
        service_schema["filters"].update(todo_id=[todo_id])
        assert service.GetTasksQuery.model_validate(service_schema)

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_invalid_list_tasks_query_to_service_schema(self):
        args = {
            "limit": "hello",
            "offset": -4,
            "task_id": [1, 2, 3],
        }
        query_args = ListTasksQueryArgs.model_validate(args)
        service_schema = query_args.to_service_query_schema()
        service.GetTasksQuery.model_validate(service_schema)

    def test_tasklist_valid_data_with_tasks(self):
        task = Task(
            task_id=1,
            brief="brief",
            todo_id=1,
            status=TaskStatus.COMPLETE,
            priority=TaskPriority.HIGH,
            category="category",
            due=now,
            created_at=now,
            updated_at=now,
        )
        assert TaskList(tasks=[task for _ in range(5)])

    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_tasklist_invalid_data(self):
        invalid_task = {
            "task_id": 1,
            "brief": "brief",
            "todo_id": 1,
            "status": TaskStatus.COMPLETE,
            "priority": TaskPriority.HIGH,
            "category": "category",
        }
        assert TaskList(tasks=[invalid_task for _ in range(5)])

    def test_create_task_no_todo_id(self):
        task = CreateTask(brief="brief", todo_id=1, category="category")
        task = task.model_dump()
        task.pop("todo_id")
        assert CreateTaskNoTodoId.model_validate(task)
