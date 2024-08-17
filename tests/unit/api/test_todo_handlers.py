from http import HTTPStatus
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from humps import decamelize

from main import app
from src.domain.models import Task, Todo, UpdateTodo
from src.domain.types import TaskPriority, TaskStatus, TodoStatus
from src.service.todo import TodoService
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
valid_todo = Todo(
    todo_id=1,
    owner="bob",
    status=TodoStatus.ACTIVE,
    created_at=now,
    updated_at=now,
    tasks=[valid_task for _ in range(3)],
)


class TestTodoHandlers:
    transport = httpx.ASGITransport(app)
    client: httpx.AsyncClient = None

    @pytest.fixture(autouse=True, scope="module")
    def setup(self):
        self.__class__.client = httpx.AsyncClient(
            transport=self.transport, base_url="http://testserver"
        )

    @patch.object(TodoService, "get_many", return_value=[valid_todo])
    async def test_list_todos_without_query_args(self, mock: AsyncMock):
        resp = await self.client.get("/todos/")

        mock.assert_awaited_once_with(
            limit=DEFAULT_LIMIT, offset=0, filters={}
        )
        assert resp.status_code == HTTPStatus.OK
        body = resp.json()
        assert "todos" in body
        assert len(body["todos"]) > 0

    @patch.object(TodoService, "get_many", return_value=[valid_todo])
    async def test_list_todos_with_single_query_arg(self, mock: AsyncMock):
        owner = "bob"
        resp = await self.client.get(f"/todos/?owner={owner}")

        mock.assert_awaited_once_with(
            limit=DEFAULT_LIMIT, offset=0, filters={"owner": [owner]}
        )
        assert resp.status_code == HTTPStatus.OK
        body = resp.json()
        assert "todos" in body
        assert len(body["todos"]) > 0

    @patch.object(TodoService, "get_many", return_value=[valid_todo])
    async def test_list_todos_with_multiple_query_args(self, mock: AsyncMock):
        limit = 14
        offset = 1
        owner = ["bob", "alice"]
        status = TodoStatus.INACTIVE

        resp = await self.client.get(
            f"/todos/?limit={limit}&offset={offset}"
            f"&owner={owner[0]}&owner={owner[1]}&status={status}"
        )

        mock.assert_awaited_once_with(
            limit=limit,
            offset=offset,
            filters={"owner": owner, "status": [status]},
        )
        assert resp.status_code == HTTPStatus.OK
        body = resp.json()
        assert "todos" in body
        assert len(body["todos"]) > 0

    @patch.object(TodoService, "get_many")
    async def test_list_todos_with_negative_limit(self, mock: AsyncMock):
        limit = -1
        resp = await self.client.get(f"/todos/?limit={limit}")

        mock.assert_not_awaited()
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    @patch.object(TodoService, "get_many")
    async def test_list_todos_with_negative_offset(self, mock: AsyncMock):
        offset = -1
        resp = await self.client.get(f"/todos/?offset={offset}")

        mock.assert_not_awaited()
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    @patch.object(TodoService, "get_many")
    async def test_list_todos_with_limit_too_high(self, mock: AsyncMock):
        limit = 101
        resp = await self.client.get(f"/todos/?limit={limit}")

        mock.assert_not_awaited()
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    @patch.object(TodoService, "get_many")
    async def test_list_todos_with_invalid_filters(self, mock: AsyncMock):
        status = "invalid"
        resp = await self.client.get(f"/todos/?status={status}")

        mock.assert_not_awaited()
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    @patch.object(TodoService, "get_many")
    async def test_list_todos_extra_args(self, mock: AsyncMock):
        extra = "extra"
        resp = await self.client.get(f"/todos/?extra={extra}")

        mock.assert_not_awaited()
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    @patch.object(TodoService, "get_many", return_value=[])
    async def test_list_todos_with_empty_service_response(
        self, mock: AsyncMock
    ):
        resp = await self.client.get("/todos/")

        mock.assert_awaited_once()
        assert resp.status_code == HTTPStatus.OK
        body = resp.json()
        assert "todos" in body
        assert len(body["todos"]) == 0

    @patch.object(TodoService, "create", return_value=valid_todo)
    async def test_add_todo_with_valid_partial_payload(self, mock: AsyncMock):
        payload = {"owner": "bob"}
        resp = await self.client.post("/todos/", json=payload)

        mock.assert_awaited_once_with(**payload, status=TodoStatus.ACTIVE)
        assert resp.status_code == HTTPStatus.CREATED
        assert Todo.model_validate(decamelize(resp.json()))

    @patch.object(TodoService, "create", return_value=valid_todo)
    async def test_add_todo_with_valid_complete_payload(self, mock: AsyncMock):
        payload = {"owner": "bob", "status": TodoStatus.ACTIVE}
        resp = await self.client.post("/todos/", json=payload)

        mock.assert_awaited_once_with(**payload)
        assert resp.status_code == HTTPStatus.CREATED
        assert Todo.model_validate(decamelize(resp.json()))

    @patch.object(TodoService, "create")
    async def test_add_todo_with_invalid_owner_value_type(
        self, mock: AsyncMock
    ):
        payload = {"owner": 12, "status": TodoStatus.INACTIVE}

        resp = await self.client.post("/todos/", json=payload)

        mock.assert_not_awaited()
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    @patch.object(TodoService, "create")
    async def test_add_todo_with_missing_required_owner_value(
        self, mock: AsyncMock
    ):
        payload = {"status": TodoStatus.INACTIVE}

        resp = await self.client.post("/todos/", json=payload)

        mock.assert_not_awaited()
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    @patch.object(TodoService, "create")
    async def test_add_todo_with_extra_payload(self, mock: AsyncMock):
        payload = {
            "owner": "bob",
            "status": TodoStatus.INACTIVE,
            "extra": "extra",
        }

        resp = await self.client.post("/todos/", json=payload)

        mock.assert_not_awaited()
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    @patch.object(TodoService, "get_one", return_value=valid_todo)
    async def test_get_todo_without_prefetch(self, mock: AsyncMock):
        todo_id, default_prefetch = 1, 0
        resp = await self.client.get(f"/todos/{todo_id}/")

        mock.assert_awaited_once_with(
            todo_id=todo_id, prefetch_tasks=default_prefetch
        )
        assert resp.status_code == HTTPStatus.OK
        assert Todo.model_validate(decamelize(resp.json()))

    @patch.object(TodoService, "get_one", return_value=valid_todo)
    async def test_get_todo_with_prefetch(self, mock: AsyncMock):
        todo_id, prefetch = 1, 10
        resp = await self.client.get(
            f"/todos/{todo_id}/?prefetch_tasks={prefetch}"
        )

        mock.assert_awaited_once_with(todo_id=todo_id, prefetch_tasks=prefetch)
        assert resp.status_code == HTTPStatus.OK
        assert Todo.model_validate(decamelize(resp.json()))

    @patch.object(TodoService, "get_one")
    async def test_get_todo_with_negative_id(self, mock: AsyncMock):
        resp = await self.client.get("/todos/-1/")

        mock.assert_not_awaited()
        assert resp.status_code == HTTPStatus.NOT_FOUND

    @patch.object(TodoService, "get_one")
    async def test_get_todo_with_invalid_id_value_type(self, mock: AsyncMock):
        resp = await self.client.get("/todos/hello/")

        mock.assert_not_awaited()
        assert resp.status_code == HTTPStatus.NOT_FOUND

    @patch.object(TodoService, "get_one")
    async def test_get_todo_with_negative_prefetch(self, mock: AsyncMock):
        resp = await self.client.get("/todos/1/?prefetch_tasks=-1")

        mock.assert_not_awaited()
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    @patch.object(TodoService, "get_one", return_value=None)
    async def test_get_todo_does_not_exist(self, mock: AsyncMock):
        todo_id, default_prefetch = 1, 0
        resp = await self.client.get(f"/todos/{todo_id}/")

        mock.assert_awaited_once_with(
            todo_id=todo_id, prefetch_tasks=default_prefetch
        )
        assert resp.status_code == HTTPStatus.NOT_FOUND
        assert resp.content.decode() == f"Todo with id {todo_id} not found"

    @patch.object(TodoService, "update", return_value=valid_todo)
    async def test_update_todo_valid_complete_payload(self, mock: AsyncMock):
        todo_id = 1
        payload = {
            "owner": "bob",
            "status": TodoStatus.INACTIVE,
            "created_at": "2021-09-12 14:05:02",
            "updated_at": "2022-09-12 14:05:02",
        }

        resp = await self.client.patch(f"/todos/{todo_id}/", json=payload)

        mock.assert_awaited_once_with(
            todo_id=todo_id, payload=UpdateTodo(**payload)
        )
        assert resp.status_code == HTTPStatus.OK
        assert Todo.model_validate(decamelize(resp.json()))

    @patch.object(TodoService, "update", return_value=valid_todo)
    async def test_update_todo_valid_partial_payload(self, mock: AsyncMock):
        todo_id, payload = 1, {"owner": "bob"}

        resp = await self.client.patch(f"/todos/{todo_id}/", json=payload)

        mock.assert_awaited_once_with(
            todo_id=todo_id, payload=UpdateTodo(**payload)
        )
        assert resp.status_code == HTTPStatus.OK
        assert Todo.model_validate(decamelize(resp.json()))

    @patch.object(TodoService, "update", return_value=None)
    async def test_update_todo_does_not_exit(self, mock: AsyncMock):
        todo_id, payload = 1, {"owner": "bob"}

        resp = await self.client.patch(f"/todos/{todo_id}/", json=payload)

        mock.assert_awaited_once_with(
            todo_id=todo_id, payload=UpdateTodo(**payload)
        )
        assert resp.status_code == HTTPStatus.NOT_FOUND
        assert resp.content.decode() == f"Todo with id {todo_id} not found"

    @patch.object(TodoService, "update")
    async def test_update_todo_invalid_payload(self, mock: AsyncMock):
        todo_id, payload = 1, {"owner": 173}

        resp = await self.client.patch(f"/todos/{todo_id}/", json=payload)

        mock.assert_not_awaited()
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    @patch.object(TodoService, "update")
    async def test_update_todo_with_extra_field(self, mock: AsyncMock):
        todo_id = 1
        payload = {"owner": "bob", "extra": "extra"}

        resp = await self.client.patch(f"/todos/{todo_id}/", json=payload)

        mock.assert_not_awaited()
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    @patch.object(TodoService, "update")
    async def test_update_todo_empty_pyaload(self, mock: AsyncMock):
        resp = await self.client.patch("/todos/1/", json={"owner": None})

        mock.assert_not_awaited()
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    @patch.object(TodoService, "delete", return_value=True)
    async def test_delete_existing_todo(self, mock: AsyncMock):
        todo_id = 1
        resp = await self.client.delete(f"/todos/{todo_id}/")

        mock.assert_awaited_once_with(todo_id=todo_id)
        assert resp.status_code == HTTPStatus.NO_CONTENT

    @patch.object(TodoService, "delete", return_value=False)
    async def test_delete_todo_does_not_exist(self, mock: AsyncMock):
        todo_id = 1
        resp = await self.client.delete(f"/todos/{todo_id}/")

        mock.assert_awaited_once_with(todo_id=todo_id)
        assert resp.status_code == HTTPStatus.NOT_FOUND
        resp.content == f"Todo with id {todo_id} not found"

    @patch.object(TodoService, "delete")
    async def test_delete_todo_invalid_todo_id(self, mock: AsyncMock):
        todo_id = -1

        with patch.object(TodoService, "delete") as mock:
            resp = await self.client.delete(f"/todos/{todo_id}/")

        mock.assert_not_awaited()
        assert resp.status_code == HTTPStatus.NOT_FOUND
        resp.content == f"Todo with id {todo_id} not found"
