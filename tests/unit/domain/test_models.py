from datetime import datetime

import pytest
from pydantic import ValidationError

from src.data.result import TaskRow, TodoRow
from src.domain.models import CreateTask, CreateTodo, Task, Todo, UpdateTask, UpdateTodo
from src.domain.types import TaskPriority, TaskStatus, TodoStatus
from src.utils import now as now_

now = now_()

class TestTodoModels:
    def test_todo_model_required_args_only(self):
        todo = {
            "todo_id": 1,
            "owner": "bob",
            "status": TodoStatus.ACTIVE,
            "created_at": now,
            "updated_at": now,
            "tasks": None,
        }
        todo = TodoRow(**todo)
        validated = Todo.model_validate(todo)
        assert validated
        assert validated.todo_id == todo.todo_id
        assert validated.owner == todo.owner
        assert validated.status == todo.status
        assert validated.created_at == todo.created_at
        assert validated.updated_at == todo.updated_at
        assert validated.tasks == todo.tasks is None


    def test_todo_model_all_args(self):
        data = {
            "task_id": 1,
            "brief": "brief1",
            "todo_id": 1,
            "contents": "contents2",
            "status": TaskStatus.COMPLETE,
            "priority": TaskPriority.HIGH,
            "category": "category2",
            "due": now,
            "created_at": now,
            "updated_at": now,
        }
        tasks = (TaskRow(**data) for _ in range(3))
        todo = {
            "todo_id": 1,
            "owner": "bob",
            "status": TodoStatus.ACTIVE,
            "created_at": now,
            "updated_at": now,
            "tasks": tasks,
        }
        todo = TodoRow(**todo)
        validated = Todo.model_validate(todo)
        assert validated
        assert validated.todo_id == todo.todo_id
        assert validated.owner == todo.owner
        assert validated.status == todo.status
        assert validated.created_at == todo.created_at
        assert validated.updated_at == todo.updated_at
        assert all(Task.model_validate(task) for task in validated.tasks)


    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_todo_model_extra_attr(self):
        todo = {
            "todo_id": 1,
            "owner": "bob",
            "status": TodoStatus.ACTIVE,
            "created_at": now,
            "updated_at": now,
            "tasks": None,
            "extra": "extra",
        }
        Todo.model_validate(todo)


    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_todo_model_missing_required_attr(self):
        todo = {
            "todo_id": None,
            "owner": "bob",
            "status": TodoStatus.ACTIVE,
            "created_at": now,
            "updated_at": now,
            "tasks": None,
        }
        Todo.model_validate(TodoRow(**todo))


    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_todo_model_invalid_status(self):
        todo = {
            "todo_id": 1,
            "owner": "bob",
            "status": "invalid_status",
            "created_at": now,
            "updated_at": now,
            "tasks": None,
        }
        Todo.model_validate(TodoRow(**todo))


    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_todo_model_negative_todo(self):
        todo = {
            "todo_id": -1,
            "owner": "bob",
            "status": "invalid_status",
            "created_at": now,
            "updated_at": now,
            "tasks": None,
        }
        Todo.model_validate(TodoRow(**todo))


    def test_create_todo_required_args(self):
        payload = {"owner": "bob"}
        todo = CreateTodo.model_validate(payload)
        assert todo
        assert todo.owner == payload["owner"]
        assert todo.status == TodoStatus.ACTIVE


    def test_create_todo_all_args(self):
        payload = {"owner": "bob", "status": TodoStatus.INACTIVE}
        todo = CreateTodo.model_validate(payload)
        assert todo
        assert todo.owner == payload["owner"]
        assert todo.status == payload["status"]


    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_create_todo_extra_arg(self):
        payload = {"owner": "bob", "extra": "extra"}
        CreateTodo.model_validate(payload)


    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_create_todo_missing_required_filed(self):
        payload = {"status": TodoStatus.INACTIVE}
        CreateTodo.model_validate(payload)


    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_create_todo_invalid_arg_type(self):
        payload = {"owner": "bob", "status": "Invalid"}
        CreateTodo.model_validate(payload)


    def test_update_todo_some_args(self):
        payload = {"owner": "bob"}
        todo = UpdateTodo.model_validate(payload)
        assert todo
        assert todo.owner == payload["owner"]
        assert todo.status is None
        assert todo.created_at is None
        assert todo.updated_at is None


    def test_update_todo_all_args(self):
        payload = {
            "owner": "bob",
            "status": TodoStatus.INACTIVE,
            "created_at": now,
            "updated_at": now,
        }
        todo = UpdateTodo.model_validate(payload)
        assert todo
        assert todo.owner == payload["owner"]
        assert todo.status == payload["status"]
        assert todo.created_at == payload["created_at"]
        assert todo.updated_at == payload["updated_at"]


    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_update_todo_empty_payload(self):
        UpdateTodo.model_validate({})


    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_update_todo_extra_arg(self):
        payload = {"owner": "bob", "extra": "extra"}
        UpdateTodo.model_validate(payload)


    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_update_todo_invalid_arg_type(self):
        payload = {"owner": "bob", "status": "Invalid"}
        UpdateTodo.model_validate(payload)


class TestTaskModels:
    def test_task_model_required_args_only(self):
        task = {
            "task_id": 1,
            "brief": "brief1",
            "todo_id": 1,
            "contents": None,
            "status": TaskStatus.COMPLETE,
            "priority": TaskPriority.HIGH,
            "category": "category2",
            "due": now,
            "created_at": now,
            "updated_at": now,
        }
        task = TaskRow(**task)
        validated = Task.model_validate(task)
        assert validated
        assert validated.task_id == task.task_id
        assert validated.brief == task.brief
        assert validated.todo_id == task.todo_id
        assert validated.contents == task.contents is None
        assert validated.status == task.status
        assert validated.priority == task.priority
        assert validated.category == task.category
        assert validated.due == task.due
        assert validated.created_at == task.created_at
        assert validated.updated_at == task.updated_at


    def test_task_model_all_args(self):
        task = {
            "task_id": 1,
            "brief": "brief1",
            "todo_id": 1,
            "contents": "contents",
            "status": TaskStatus.COMPLETE,
            "priority": TaskPriority.HIGH,
            "category": "category2",
            "due": now,
            "created_at": now,
            "updated_at": now,
        }
        task = TaskRow(**task)
        validated = Task.model_validate(task)
        assert validated
        assert validated.task_id == task.task_id
        assert validated.brief == task.brief
        assert validated.todo_id == task.todo_id
        assert validated.contents == task.contents
        assert validated.status == task.status
        assert validated.priority == task.priority
        assert validated.category == task.category
        assert validated.due == task.due
        assert validated.created_at == task.created_at
        assert validated.updated_at == task.updated_at


    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_task_model_extra_attr(self):
        task = {
            "task_id": 1,
            "brief": "brief1",
            "todo_id": 1,
            "contents": "contents",
            "status": TaskStatus.COMPLETE,
            "priority": TaskPriority.HIGH,
            "category": "category2",
            "due": now,
            "created_at": now,
            "updated_at": now,
            "extra": "extra",
        }
        Task.model_validate(task)


    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_task_model_missing_required_attr(self):
        task = {
            "task_id": 1,
            "brief": None,
            "todo_id": 1,
            "contents": "contents",
            "status": TaskStatus.COMPLETE,
            "priority": TaskPriority.HIGH,
            "category": "category2",
            "due": now,
            "created_at": now,
            "updated_at": now,
        }
        Task.model_validate(TaskRow(**task))


    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_task_model_invalid_priority(self):
        task = {
            "task_id": 1,
            "brief": "brief1",
            "todo_id": 1,
            "contents": "contents",
            "status": TaskStatus.COMPLETE,
            "priority": "Invalid Priority",
            "category": "category2",
            "due": now,
            "created_at": now,
            "updated_at": now,
        }
        Task.model_validate(TaskRow(**task))


    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_task_model_negative_task_id(self):
        task = {
            "task_id": 1,
            "brief": "brief1",
            "todo_id": 1,
            "contents": "contents",
            "status": TaskStatus.COMPLETE,
            "priority": "Invalid Priority",
            "category": "category2",
            "due": now,
            "created_at": now,
            "updated_at": now,
        }
        Task.model_validate(TaskRow(**task))

    def test_create_task_required_args(self):
        payload = {
            "brief": "brief1",
            "todo_id": 1,
            "category": "category2",
        }
        task = CreateTask.model_validate(payload)
        assert task
        assert task.brief == payload["brief"]
        assert task.todo_id == payload["todo_id"]
        assert task.category == payload["category"]
        assert task.status == TaskStatus.PENDING
        assert task.priority == TaskPriority.LOW
        assert isinstance(task.due, datetime)
        assert task.contents is None


    def test_create_task_all_args(self):
        payload = {
            "brief": "brief1",
            "todo_id": 1,
            "contents": "contents",
            "status": TaskStatus.COMPLETE,
            "priority": TaskPriority.HIGH,
            "category": "category2",
            "due": now,
        }
        task = CreateTask.model_validate(payload)
        assert task
        assert task.brief == payload["brief"]
        assert task.todo_id == payload["todo_id"]
        assert task.category == payload["category"]
        assert task.status == payload["status"]
        assert task.priority == payload["priority"]
        assert task.due == payload["due"]
        assert task.contents == payload["contents"]


    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_create_task_extra_arg(self):
        payload = {
            "brief": "brief1",
            "todo_id": 1,
            "category": "category2",
            "extra": "extra",
        }
        CreateTask.model_validate(payload)


    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_create_task_missing_required_filed(self):
        payload = {
            "brief": "brief1",
            "todo_id": 1,
        }
        CreateTask.model_validate(payload)


    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_create_task_invalid_arg_type(self):
        payload = {
            "brief": 75,
            "todo_id": 1,
            "category": "category2",
        }
        CreateTask.model_validate(payload)


    def test_update_task_some_args(self):
        payload = {"brief": "brief2", "todo_id": 17}
        task = UpdateTask.model_validate(payload)
        assert task
        assert task.brief == payload["brief"]
        assert task.todo_id == payload["todo_id"]
        assert task.contents is None
        assert task.status is None
        assert task.priority is None
        assert task.category is None
        assert task.due is None
        assert task.created_at is None
        assert task.updated_at is None


    def test_update_task_all_args(self):
        payload = {
            "brief": "brief1",
            "todo_id": 1,
            "contents": "contents",
            "status": TaskStatus.COMPLETE,
            "priority": TaskPriority.HIGH,
            "category": "category2",
            "due": now,
            "created_at": now,
            "updated_at": now,
        }
        task = UpdateTask.model_validate(payload)
        assert task
        assert task.brief == payload["brief"]
        assert task.todo_id == payload["todo_id"]
        assert task.contents == payload["contents"]
        assert task.status == payload["status"]
        assert task.priority == payload["priority"]
        assert task.category == payload["category"]
        assert task.due == payload["due"]
        assert task.created_at == payload["created_at"]
        assert task.updated_at == payload["updated_at"]


    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_update_task_empty_payload(self):
        UpdateTask.model_validate({})


    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_update_task_extra_arg(self):
        payload = {"contents": "contents1", "extra": "extra"}
        UpdateTask.model_validate(payload)


    @pytest.mark.xfail(strict=True, raises=ValidationError)
    def test_update_task_invalid_arg_type(self):
        payload = {"brief": "brief1", "status": "Invalid"}
        UpdateTask.model_validate(payload)
