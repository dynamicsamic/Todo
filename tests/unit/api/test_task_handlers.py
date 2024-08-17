from datetime import timedelta
from http import HTTPStatus
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from humps import decamelize

from main import app
from src.domain.models import Task, UpdateTask
from src.domain.types import TaskPriority, TaskStatus
from src.service.task import TaskService
from src.settings import settings
from src.utils import now as now_
from tests.fixtures import test_client  # noqa

pytestmark = pytest.mark.asyncio
DEFAULT_LIMIT = settings.DEFAULT_PAGE_LIMIT
now = now_()

valid_task = Task(
    task_id=1,
    brief="brief1",
    todo_id=1,
    contents="contents2",
    status=TaskStatus.COMPLETE,
    priority=TaskPriority.HIGH,
    category="category2",
    due=now,
    created_at=now,
    updated_at=now,
)


class TestTaskHandlers:
    transport = httpx.ASGITransport(app)
    client: httpx.AsyncClient = None

    @pytest.fixture(autouse=True, scope="module")
    def setup(self):
        self.__class__.client = httpx.AsyncClient(
            transport=self.transport, base_url="http://testserver"
        )

    @patch.object(TaskService, "get_many", return_value=[valid_task])
    async def test_list_tasks_without_query_args(self, mock: AsyncMock):
        todo_id = 1
        resp = await self.client.get(f"/todos/{todo_id}/tasks/")

        mock.assert_awaited_once_with(
            limit=DEFAULT_LIMIT, offset=0, filters={"todo_id": [todo_id]}
        )
        assert resp.status_code == HTTPStatus.OK
        body = resp.json()
        assert "tasks" in body
        assert len(body["tasks"]) > 0

    @patch.object(TaskService, "get_many", return_value=[valid_task])
    async def test_list_tasks_with_single_query_arg(self, mock: AsyncMock):
        todo_id = 1
        category = "category"
        resp = await self.client.get(
            f"/todos/{todo_id}/tasks/?category={category}"
        )

        mock.assert_awaited_once_with(
            limit=DEFAULT_LIMIT,
            offset=0,
            filters={"category": [category], "todo_id": [todo_id]},
        )
        assert resp.status_code == HTTPStatus.OK
        body = resp.json()
        assert "tasks" in body
        assert len(body["tasks"]) > 0

    @patch.object(TaskService, "get_many", return_value=[valid_task])
    async def test_list_tasks_with_multiple_query_args(self, mock: AsyncMock):
        todo_id = 1
        limit = 14
        offset = 1
        brief = ["brief1", "brief2"]
        status = TaskStatus.COMPLETE

        resp = await self.client.get(
            f"/todos/{todo_id}/tasks/?limit={limit}&offset={offset}"
            f"&brief={brief[0]}&brief={brief[1]}&status={status}"
        )

        mock.assert_awaited_once_with(
            limit=limit,
            offset=offset,
            filters={
                "brief": ["brief1", "brief2"],
                "status": [status],
                "todo_id": [todo_id],
            },
        )
        assert resp.status_code == HTTPStatus.OK
        body = resp.json()
        assert "tasks" in body
        assert len(body["tasks"]) > 0

    @patch.object(TaskService, "get_many")
    async def test_list_tasks_with_negative_limit(self, mock: AsyncMock):
        limit = -1
        resp = await self.client.get(f"/todos/1/tasks/?limit={limit}")

        mock.assert_not_awaited()
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    @patch.object(TaskService, "get_many")
    async def test_list_tasks_with_negative_offset(self, mock: AsyncMock):
        offset = -1
        resp = await self.client.get(f"/todos/1/tasks/?offset={offset}")

        mock.assert_not_awaited()
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    @patch.object(TaskService, "get_many")
    async def test_list_tasks_with_limit_too_high(self, mock: AsyncMock):
        limit = 101
        resp = await self.client.get(f"/todos/1/tasks/?limit={limit}")

        mock.assert_not_awaited()
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    @patch.object(TaskService, "get_many")
    async def test_list_tasks_with_invalid_filters(self, mock: AsyncMock):
        status = "invalid"
        resp = await self.client.get(f"/todos/1/tasks/?status={status}")

        mock.assert_not_awaited()
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    @patch.object(TaskService, "get_many")
    async def test_list_tasks_extra_args(self, mock: AsyncMock):
        extra = "extra"
        resp = await self.client.get(f"/todos/1/tasks/?extra={extra}")

        mock.assert_not_awaited()
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    @patch.object(TaskService, "get_many", return_value=[])
    async def test_list_tasks_with_empty_service_response(
        self, mock: AsyncMock
    ):
        resp = await self.client.get("/todos/1/tasks/")

        mock.assert_awaited_once()
        assert resp.status_code == HTTPStatus.OK
        body = resp.json()
        assert "tasks" in body
        assert len(body["tasks"]) == 0

    @patch.object(TaskService, "create", return_value=valid_task)
    async def test_add_task_with_valid_partial_payload(self, mock: AsyncMock):
        todo_id = 1
        payload = {"brief": "brief", "category": "category"}
        resp = await self.client.post(f"/todos/{todo_id}/tasks/", json=payload)

        due = mock.await_args.kwargs.pop("due")
        assert due - now > timedelta(days=1)
        mock.assert_awaited_once_with(
            **payload,
            todo_id=todo_id,
            status=TaskStatus.PENDING,
            priority=TaskPriority.LOW,
        )
        assert resp.status_code == HTTPStatus.CREATED
        assert Task.model_validate(decamelize(resp.json()))

    @patch.object(TaskService, "create", return_value=valid_task)
    async def test_add_task_with_valid_complete_payload(self, mock: AsyncMock):
        todo_id = 1
        payload = {
            "brief": "brief1",
            "contents": "contents2",
            "status": TaskStatus.COMPLETE,
            "priority": TaskPriority.HIGH,
            "category": "category2",
            "due": f"{now:%Y-%m-%d %H:%M:%S}",
        }
        resp = await self.client.post(f"/todos/{todo_id}/tasks/", json=payload)

        due = payload.pop("due")
        due_ = mock.await_args.kwargs.pop("due")
        assert f"{due_:%Y-%m-%d %H:%M:%S}" == due
        mock.assert_awaited_once_with(**payload, todo_id=todo_id)
        assert resp.status_code == HTTPStatus.CREATED
        assert Task.model_validate(decamelize(resp.json()))

    @patch.object(TaskService, "create")
    async def test_add_task_with_invalid_status(self, mock: AsyncMock):
        payload = {"brief": 12, "status": TaskStatus.PENDING}
        resp = await self.client.post("/todos/1/tasks/", json=payload)

        mock.assert_not_awaited()
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    @patch.object(TaskService, "create")
    async def test_add_task_with_missing_required_category_value(
        self, mock: AsyncMock
    ):
        payload = {"brief": "brief", "status": TaskStatus.COMPLETE}
        resp = await self.client.post("/todos/1/tasks/", json=payload)

        mock.assert_not_awaited()
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    @patch.object(TaskService, "create")
    async def test_add_task_with_extra_payload(self, mock: AsyncMock):
        payload = {"brief": "brief", "category": "category", "extra": "extra"}
        resp = await self.client.post("/todos/1/tasks/", json=payload)

        mock.assert_not_awaited()
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    @patch.object(TaskService, "get_one", return_value=valid_task)
    async def test_get_task_with_valid_todo_and_task_ids(
        self, mock: AsyncMock
    ):
        todo_id, task_id = 1, 10
        resp = await self.client.get(f"/todos/{todo_id}/tasks/{task_id}/")

        mock.assert_awaited_once_with(task_id=task_id)
        assert resp.status_code == HTTPStatus.OK
        assert Task.model_validate(decamelize(resp.json()))

    @patch.object(TaskService, "get_one")
    async def test_get_task_with_negative_todo_id(self, mock: AsyncMock):
        resp = await self.client.get("/todos/-1/tasks/1/")
        mock.assert_not_awaited()
        assert resp.status_code == HTTPStatus.NOT_FOUND

    @patch.object(TaskService, "get_one")
    async def test_get_task_with_negative_task_id(self, mock: AsyncMock):
        resp = await self.client.get("/todos/1/tasks/-1/")

        mock.assert_not_awaited()
        assert resp.status_code == HTTPStatus.NOT_FOUND

    @patch.object(TaskService, "get_one", return_value=None)
    async def test_get_task_does_not_exist(self, mock: AsyncMock):
        todo_id, task_id = 1, 1
        resp = await self.client.get(f"/todos/{todo_id}/tasks/{task_id}/")

        mock.assert_awaited_once_with(task_id=task_id)
        assert resp.status_code == HTTPStatus.NOT_FOUND
        err_message = resp.content.decode()
        assert (
            err_message
            == f"Task with id {task_id} or Todo list with id {todo_id} not found"
        )

    @patch.object(TaskService, "update", return_value=valid_task)
    async def test_update_task_valid_complete_payload(self, mock: AsyncMock):
        task_id = 1
        date = f"{now:%Y-%m-%d %H:%M:%S}"
        payload = {
            "brief": "brief",
            "todo_id": 2,
            "category": "cateogry2",
            "status": TaskStatus.POSTPONED,
            "priority": TaskPriority.HIGH,
            "due": date,
            "created_at": date,
            "updated_at": date,
        }

        resp = await self.client.patch(
            f"/todos/1/tasks/{task_id}/", json=payload
        )

        mock.assert_awaited_once_with(
            task_id=task_id, payload=UpdateTask(**payload)
        )
        assert resp.status_code == HTTPStatus.OK
        assert Task.model_validate(decamelize(resp.json()))

    @patch.object(TaskService, "update", return_value=valid_task)
    async def test_update_task_valid_partial_payload(self, mock: AsyncMock):
        task_id, payload = 1, {"brief": "brief"}
        resp = await self.client.patch(
            f"/todos/1/tasks/{task_id}/", json=payload
        )

        mock.assert_awaited_once_with(
            task_id=task_id, payload=UpdateTask(**payload)
        )
        assert resp.status_code == HTTPStatus.OK
        assert Task.model_validate(decamelize(resp.json()))

    @patch.object(TaskService, "update", return_value=None)
    async def test_update_task_does_not_exit(self, mock: AsyncMock):
        todo_id, task_id, payload = 1, 1, {"brief": "brief"}
        resp = await self.client.patch(
            f"/todos/{todo_id}/tasks/{task_id}/", json=payload
        )

        mock.assert_awaited_once_with(
            task_id=task_id, payload=UpdateTask(**payload)
        )
        assert resp.status_code == HTTPStatus.NOT_FOUND
        err_message = resp.content.decode()
        assert (
            err_message
            == f"Task with id {task_id} or Todo list with id {todo_id} not found"
        )

    @patch.object(TaskService, "update")
    async def test_update_task_invalid_payload(self, mock: AsyncMock):
        resp = await self.client.patch("/todos/1/tasks/1/", json={"brief": 33})
        mock.assert_not_awaited()
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    @patch.object(TaskService, "update")
    async def test_update_task_with_extra_field(self, mock: AsyncMock):
        resp = await self.client.patch(
            "/todos/1/tasks/1/", json={"extra": "extra"}
        )
        mock.assert_not_awaited()
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    @patch.object(TaskService, "update")
    async def test_update_task_empty_pyaload(self, mock: AsyncMock):
        resp = await self.client.patch(
            "/todos/1/tasks/1/", json={"status": None}
        )
        mock.assert_not_awaited()
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    @patch.object(TaskService, "update")
    async def test_update_negative_task_id(self, mock: AsyncMock):
        resp = await self.client.patch(
            "/todos/1/tasks/-1/", json={"brief": "brief"}
        )
        mock.assert_not_awaited()
        assert resp.status_code == HTTPStatus.NOT_FOUND

    @patch.object(TaskService, "delete", return_value=True)
    async def test_delete_existing_task(self, mock: AsyncMock):
        task_id = 1
        resp = await self.client.delete(f"/todos/1/tasks/{task_id}/")

        mock.assert_awaited_once_with(task_id=task_id)
        assert resp.status_code == HTTPStatus.NO_CONTENT

    @patch.object(TaskService, "delete", return_value=False)
    async def test_delete_task_does_not_exist(self, mock: AsyncMock):
        todo_id, task_id = 1, 1
        resp = await self.client.delete(f"/todos/{todo_id}/tasks/{task_id}/")

        mock.assert_awaited_once_with(task_id=task_id)
        assert resp.status_code == HTTPStatus.NOT_FOUND
        resp.content == f"Task with id {task_id} or Todo list with id {todo_id} not found"

    @patch.object(TaskService, "delete")
    async def test_delete_task_negative_task_id(self, mock: AsyncMock):
        todo_id, task_id = 1, -1
        resp = await self.client.delete(f"/todos/{todo_id}/tasks/{task_id}")

        mock.assert_not_awaited()
        assert resp.status_code == HTTPStatus.NOT_FOUND
        resp.content == f"Task with id {task_id} or Todo list with id {todo_id} not found"
