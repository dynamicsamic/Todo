from http import HTTPStatus

import pytest
import pytest_asyncio
from humps import decamelize
from quart.testing import QuartClient

from main import app
from src.data.db import apply_migration, check_db_created, drop_db, load_all
from src.domain.models import Task, Todo
from src.domain.types import TaskPriority, TaskStatus, TodoStatus
from src.utils import now
from tests.conftest import DEFAULT_LIMIT, TASK_SAMPLE_SIZE, TODO_SAMPLE_SIZE

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(scope="module")
async def prepare_db():
    await check_db_created()
    await apply_migration("_000_initial")
    await load_all(TODO_SAMPLE_SIZE, TASK_SAMPLE_SIZE)
    yield
    await drop_db()


@pytest_asyncio.fixture(scope="module", autouse=True)
async def test_client(prepare_db):
    async with app.test_app() as test_app:
        yield test_app.test_client()


class TestTodoAPI:
    client: QuartClient = None
    base_url = "/api/v1/todos/"
    safely_delete_ids = []

    @pytest_asyncio.fixture(autouse=True, scope="module")
    async def setup(self, test_client):
        self.__class__.client = test_client

    async def test_check_allowed_methods_for_todos_endpoint(self):
        headers = (await self.client.options(self.base_url)).headers
        allow = headers.get("allow").split(", ")
        assert set(allow) == {"OPTIONS", "GET", "POST", "HEAD"}

    async def test_list_todos_without_query_args(self):
        resp = await self.client.get(self.base_url)
        assert resp.status_code == HTTPStatus.OK
        body = await resp.get_json()
        todos = body.get("todos")
        assert len(todos) == DEFAULT_LIMIT
        for item in todos:
            assert Todo.model_validate(decamelize(item))

    async def test_list_todos_with_limit_offset(self):
        limit, offset = 7, 4

        resp = await self.client.get(
            f"{self.base_url}?limit={limit}&offset={offset}"
        )

        assert resp.status_code == HTTPStatus.OK
        body = await resp.get_json()
        todos = body.get("todos")
        assert len(todos) == limit
        for item in todos:
            todo = Todo.model_validate(decamelize(item))
            assert todo.todo_id > offset

    async def test_list_todos_with_unique_filters(self):
        owners = ["todo1", "todo2"]
        resp = await self.client.get(
            f"{self.base_url}?owner={owners[0]}&owner={owners[1]}"
        )
        assert resp.status_code == HTTPStatus.OK

        body = await resp.get_json()
        todos = body.get("todos")
        assert len(todos) == len(owners)
        for item in todos:
            assert Todo.model_validate(decamelize(item))

    async def test_list_todos_with_generic_filters(self):
        status = TodoStatus.ACTIVE
        resp = await self.client.get(f"{self.base_url}?status={status}")

        assert resp.status_code == HTTPStatus.OK
        body = await resp.get_json()
        todos = body.get("todos")
        for item in todos:
            todo = Todo.model_validate(decamelize(item))
            assert todo.status == status

    async def test_list_todos_empty_response(self):
        date = f"{now():%Y-%m-%d %H:%M:%S}"
        resp = await self.client.get(f"{self.base_url}?created_at={date}")

        assert resp.status_code == HTTPStatus.OK
        todos = (await resp.get_json()).get("todos")
        assert todos == []

    async def test_add_todo_valid_complete_payload(self):
        payload = {"owner": "e2e_test_create1", "status": TodoStatus.INACTIVE}
        resp = await self.client.post(self.base_url, json=payload)

        assert resp.status_code == HTTPStatus.CREATED
        body = await resp.get_json()
        todo = Todo.model_validate(decamelize(body))
        assert todo.owner == payload["owner"]
        assert todo.status == payload["status"]
        self.safely_delete_ids.append(todo.todo_id)

    async def test_add_todo_valid_partial_payload(self):
        payload = {"owner": "e2e_test_create2"}
        resp = await self.client.post(self.base_url, json=payload)

        assert resp.status_code == HTTPStatus.CREATED
        body = await resp.get_json()
        todo = Todo.model_validate(decamelize(body))
        assert todo.owner == payload["owner"]
        self.safely_delete_ids.append(todo.todo_id)

    async def test_add_todo_invalid_owner_value(self):
        payload = {"owner": 5721, "status": TodoStatus.INACTIVE}
        resp = await self.client.post(self.base_url, json=payload)
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    async def test_add_todo_missing_required_owner_attr(self):
        payload = {"status": TodoStatus.INACTIVE}
        resp = await self.client.post(self.base_url, json=payload)
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    async def test_add_todo_extra_attr(self):
        payload = {"extra": "extra", "status": TodoStatus.INACTIVE}
        resp = await self.client.post(self.base_url, json=payload)
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    async def test_check_allowed_methods_for_todo_endpoint(self):
        url = f"{self.base_url}1/"
        headers = (await self.client.options(url)).headers
        allow = headers.get("allow").split(", ")
        assert set(allow) == {"OPTIONS", "GET", "PATCH", "DELETE", "HEAD"}

    async def test_get_todo_without_prefetch(self):
        todo_id = 1
        resp = await self.client.get(f"{self.base_url}{todo_id}/")
        assert resp.status_code == HTTPStatus.OK
        body = await resp.get_json()
        todo = Todo.model_validate(decamelize(body))
        assert todo.todo_id == todo_id
        assert todo.tasks is None

    async def test_get_todo_with_prefetch(self):
        todo_id, prefetch = 1, 3
        resp = await self.client.get(
            f"{self.base_url}{todo_id}/?prefetch_tasks={prefetch}"
        )
        assert resp.status_code == HTTPStatus.OK
        body = await resp.get_json()
        todo = Todo.model_validate(decamelize(body))
        assert todo.todo_id == todo_id
        tasks = todo.tasks
        assert len(tasks) == prefetch
        assert all(task.todo_id == todo_id for task in tasks)

    async def test_get_todo_with_empty_service_response(self):
        todo_id = TODO_SAMPLE_SIZE + 100
        resp = await self.client.get(f"{self.base_url}{todo_id}/")
        assert resp.status_code == HTTPStatus.NOT_FOUND
        assert (
            await resp.get_data()
        ).decode() == f"Todo with id {todo_id} not found"

    async def test_get_todo_with_invalid_todo_id(self):
        resp = await self.client.get(f"{self.base_url}invalid/")
        assert resp.status_code == HTTPStatus.NOT_FOUND

    async def test_get_todo_invalid_prefetch_id(self):
        resp = await self.client.get(
            f"{self.base_url}1/?prefetch_tasks=invalid"
        )
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    @pytest.mark.skip("timezone mismatch between api and db")
    async def test_update_todo_with_partial_payload(self):
        todo_id = 1
        date = f"{now():%Y-%m-%d %H:%M:%S}"
        payload = {"created_at": date}
        resp = await self.client.patch(
            f"{self.base_url}{todo_id}/", json=payload
        )

        assert resp.status_code == HTTPStatus.OK
        todo = Todo.model_validate(decamelize(await resp.get_json()))
        assert todo.todo_id == todo_id
        assert f"{todo.created_at:%Y-%m-%d %H:%M:%S}" == date

    @pytest.mark.skip("timezone mismatch between api and db")
    async def test_update_todo_with_complete_payload(self):
        todo_id = 1
        date = f"{now():%Y-%m-%d %H:%M:%S}"
        payload = {
            "owner": "e2e_test_update1",
            "status": TodoStatus.INACTIVE,
            "created_at": date,
            "updated_at": date,
        }
        resp = await self.client.patch(
            f"{self.base_url}{todo_id}/", json=payload
        )

        assert resp.status_code == HTTPStatus.OK
        todo = Todo.model_validate(decamelize(await resp.get_json()))
        assert todo.todo_id == todo_id
        assert todo.owner == payload["owner"]
        assert todo.status == payload["status"]
        assert f"{todo.created_at:%Y-%m-%d %H:%M:%S}" == date
        assert f"{todo.created_at:%Y-%m-%d %H:%M:%S}" == date

    async def test_update_todo_with_empty_payload(self):
        resp = await self.client.patch(f"{self.base_url}1/", json={})
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    async def test_update_todo_with_invalid_value(self):
        resp = await self.client.patch(
            f"{self.base_url}1/", json={"status": "invalid"}
        )
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    async def test_update_todo_with_extra_attr(self):
        resp = await self.client.patch(
            f"{self.base_url}1/", json={"extra": "extra"}
        )
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    async def test_update_todo_does_not_exist(self):
        todo_id = TODO_SAMPLE_SIZE + 100
        resp = await self.client.patch(
            f"{self.base_url}{todo_id}/", json={"owner": "owner"}
        )
        assert resp.status_code == HTTPStatus.NOT_FOUND

    async def test_delete_todo_valid_todo_id(self):
        todo_id = self.safely_delete_ids.pop()
        url = f"{self.base_url}{todo_id}/"

        resp = await self.client.delete(url)
        assert resp.status_code == HTTPStatus.NO_CONTENT

        todo = await self.client.get(url)
        assert (await todo.get_json()) is None

    async def test_delete_todo_invalid_todo_id(self):
        resp = await self.client.delete(f"{self.base_url}-1/")
        assert resp.status_code == HTTPStatus.NOT_FOUND

    async def test_delete_todo_does_not_exist(self):
        todo_id = TODO_SAMPLE_SIZE + 100
        resp = await self.client.delete(f"{self.base_url}{todo_id}/")
        assert resp.status_code == HTTPStatus.NOT_FOUND


class TestTaskAPI:
    client: QuartClient = None
    base_url = "/api/v1/todos/"
    new_tasks = []

    @pytest_asyncio.fixture(autouse=True, scope="module")
    async def setup(self, test_client):
        self.__class__.client = test_client

    def get_task(self) -> tuple[int, int]:
        try:
            return self.new_tasks.pop()
        except IndexError:
            return (1, TASK_SAMPLE_SIZE)

    async def test_check_allowed_methods_for_tasks_endpoint(self):
        url = f"{self.base_url}1/tasks/"
        headers = (await self.client.options(url)).headers
        allow = headers.get("allow").split(", ")
        assert set(allow) == {"OPTIONS", "GET", "POST", "HEAD"}

    async def test_list_tasks_without_query_args(self):
        resp = await self.client.get(f"{self.base_url}1/tasks/")
        assert resp.status_code == HTTPStatus.OK
        body = await resp.get_json()
        tasks = body.get("tasks")
        assert len(tasks) == DEFAULT_LIMIT
        for item in tasks:
            assert Task.model_validate(decamelize(item))

    async def test_list_tasks_with_limit_offset(self):
        limit, offset = 7, 4

        resp = await self.client.get(
            f"{self.base_url}1/tasks/?limit={limit}&offset={offset}"
        )

        assert resp.status_code == HTTPStatus.OK
        body = await resp.get_json()
        tasks = body.get("tasks")
        assert len(tasks) == limit
        for item in tasks:
            task = Task.model_validate(decamelize(item))
            assert task.task_id > offset

    async def test_list_tasks_with_unique_filters(self):
        briefs = ["brief1", "brief2"]
        resp = await self.client.get(
            f"{self.base_url}1/tasks/?brief={briefs[0]}&brief={briefs[1]}"
        )
        assert resp.status_code == HTTPStatus.OK

        body = await resp.get_json()
        tasks = body.get("tasks")
        assert len(tasks) == len(briefs)
        for item in tasks:
            assert Task.model_validate(decamelize(item))

    async def test_list_tasks_with_generic_filters(self):
        status = TaskStatus.POSTPONED
        resp = await self.client.get(
            f"{self.base_url}1/tasks/?status={status}"
        )

        assert resp.status_code == HTTPStatus.OK
        body = await resp.get_json()
        tasks = body.get("tasks")
        for item in tasks:
            task = Task.model_validate(decamelize(item))
            assert task.status == status

    async def test_list_tasks_empty_response(self):
        date = f"{now():%Y-%m-%d %H:%M:%S}"
        resp = await self.client.get(
            f"{self.base_url}1/tasks/?created_at={date}"
        )

        assert resp.status_code == HTTPStatus.OK
        tasks = (await resp.get_json()).get("tasks")
        assert tasks == []

    async def test_add_task_valid_complete_payload(self):
        todo_id = 2
        payload = {
            "brief": "e2e_test_create1",
            "contents": "contents",
            "status": TaskStatus.COMPLETE,
            "priority": TaskPriority.HIGH,
            "category": "e2e_test_category",
            "due": f"{now():%Y-%m-%d %H:%M:%S}",
        }
        resp = await self.client.post(
            f"{self.base_url}{todo_id}/tasks/", json=payload
        )

        assert resp.status_code == HTTPStatus.CREATED
        body = await resp.get_json()
        task = Task.model_validate(decamelize(body))
        assert task.todo_id == todo_id
        assert task.brief == payload["brief"]
        assert task.contents == payload["contents"]
        assert task.status == payload["status"]
        assert task.priority == payload["priority"]
        assert task.category == payload["category"]
        self.new_tasks.append((task.todo_id, task.task_id))

    async def test_add_task_valid_partial_payload(self):
        todo_id = 2
        payload = {
            "brief": "e2e_test_create2",
            "category": "e2e_test_category",
        }
        resp = await self.client.post(
            f"{self.base_url}{todo_id}/tasks/", json=payload
        )

        assert resp.status_code == HTTPStatus.CREATED
        body = await resp.get_json()
        task = Task.model_validate(decamelize(body))
        assert task.todo_id == todo_id
        assert task.brief == payload["brief"]
        self.new_tasks.append((task.todo_id, task.task_id))

    async def test_add_task_invalid_brief_value(self):
        payload = {"brief": 2345, "category": "e2e_test_category"}
        resp = await self.client.post(f"{self.base_url}2/tasks/", json=payload)
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    async def test_add_task_missing_required_category_attr(self):
        payload = {"brief": "e2e_test_create2"}
        resp = await self.client.post(f"{self.base_url}2/tasks/", json=payload)
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    async def test_add_task_extra_attr(self):
        payload = {"brief": "e2e_test_create2", "extra": "extra"}
        resp = await self.client.post(f"{self.base_url}2/tasks/", json=payload)
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    async def test_check_allowed_methods_for_task_endpoint(self):
        url = f"{self.base_url}2/tasks/1/"
        headers = (await self.client.options(url)).headers
        allow = headers.get("allow").split(", ")
        assert set(allow) == {"OPTIONS", "GET", "PATCH", "DELETE", "HEAD"}

    async def test_get_task(self):
        todo_id = 1
        task_id = 1
        resp = await self.client.get(
            f"{self.base_url}{todo_id}/tasks/{task_id}/"
        )
        assert resp.status_code == HTTPStatus.OK
        body = await resp.get_json()
        task = Task.model_validate(decamelize(body))
        assert task.todo_id == todo_id
        assert task.task_id == task_id

    async def test_get_task_does_not_exist(self):
        todo_id = 1
        task_id = TASK_SAMPLE_SIZE + 100
        resp = await self.client.get(
            f"{self.base_url}{todo_id}/tasks/{task_id}/"
        )
        assert resp.status_code == HTTPStatus.NOT_FOUND
        assert (
            await resp.get_data()
        ).decode() == f"Task with id {task_id} or Todo list with id {todo_id} not found"

    async def test_get_task_with_invalid_task_id(self):
        resp = await self.client.get(f"{self.base_url}1/tasks/invalid/")
        assert resp.status_code == HTTPStatus.NOT_FOUND

    async def test_update_task_with_partial_payload(self):
        todo_id, task_id = self.get_task()
        payload = {"brief": "e2e_test_update1"}
        resp = await self.client.patch(
            f"{self.base_url}{todo_id}/tasks/{task_id}/", json=payload
        )

        assert resp.status_code == HTTPStatus.OK
        task = Task.model_validate(decamelize(await resp.get_json()))
        assert task.task_id == task_id
        assert task.todo_id == todo_id
        assert task.brief == payload["brief"]
        self.new_tasks.append((task.todo_id, task.task_id))

    @pytest.mark.skip("timezone mismatch between api and db")
    async def test_update_task_with_complete_payload(self):
        todo_id, task_id = self.get_task()
        date = f"{now():%Y-%m-%d %H:%M:%S}"
        payload = {
            "brief": "e2e_test_update2",
            "todo_id": 2,
            "contents": "e2e_test_update2",
            "status": TaskStatus.COMPLETE,
            "priority": TaskPriority.HIGH,
            "category": "e2e_test_category",
            "due": date,
            "created_at": date,
            "updated_at": date,
        }

        resp = await self.client.patch(
            f"{self.base_url}{todo_id}/tasks/{task_id}/", json=payload
        )

        assert resp.status_code == HTTPStatus.OK
        task = Task.model_validate(decamelize(await resp.get_json()))
        assert task.task_id == task_id
        assert task.todo_id == payload["todo_id"]
        assert task.brief == payload["brief"]
        assert task.contents == payload["contents"]
        assert task.status == payload["status"]
        assert task.priority == payload["priority"]
        assert task.category == payload["category"]
        assert f"{task.due:%Y-%m-%d %H:%M:%S}" == payload["due"]
        assert f"{task.created_at:%Y-%m-%d %H:%M:%S}" == payload["created_at"]
        assert f"{task.updated_at:%Y-%m-%d %H:%M:%S}" == payload["updated_at"]
        self.new_tasks.append((task.todo_id, task.task_id))

    async def test_update_task_with_empty_payload(self):
        resp = await self.client.patch(f"{self.base_url}1/tasks/1/", json={})
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    async def test_update_task_with_invalid_value(self):
        resp = await self.client.patch(
            f"{self.base_url}1/tasks/1/", json={"status": "invalid"}
        )
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    async def test_update_task_with_extra_attr(self):
        resp = await self.client.patch(
            f"{self.base_url}1/tasks/1/", json={"extra": "extra"}
        )
        assert resp.status_code == HTTPStatus.BAD_REQUEST

    async def test_update_task_does_not_exist(self):
        invalid_id = TASK_SAMPLE_SIZE + 100
        resp = await self.client.patch(
            f"{self.base_url}{invalid_id}/tasks/{invalid_id}/",
            json={"brief": "brief"},
        )
        assert resp.status_code == HTTPStatus.NOT_FOUND

    async def test_delete_task_valid_task_id(self):
        todo_id, task_id = self.get_task()
        url = f"{self.base_url}{todo_id}/tasks/{task_id}/"

        resp = await self.client.delete(url)
        assert resp.status_code == HTTPStatus.NO_CONTENT

        todo = await self.client.get(url)
        assert (await todo.get_json()) is None

    async def test_delete_task_invalid_task_id(self):
        resp = await self.client.delete(f"{self.base_url}1/tasks/-1/")
        assert resp.status_code == HTTPStatus.NOT_FOUND

    async def test_delete_task_does_not_exist(self):
        task_id = TASK_SAMPLE_SIZE + 100
        resp = await self.client.delete(f"{self.base_url}1/tasks/{task_id}/")
        assert resp.status_code == HTTPStatus.NOT_FOUND
