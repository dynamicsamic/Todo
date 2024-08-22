from unittest.mock import AsyncMock, patch

import pytest

from src.data.repository import TodoRepository
from src.data.result import TaskRow, TodoRow
from src.domain.models import Todo
from src.domain.types import TaskPriority, TaskStatus, TodoStatus
from src.service.todo import TodoService
from src.service.validation import BadRequest, BadResponse
from src.utils import now as now_
from tests.conftest import DEFAULT_LIMIT

pytestmark = pytest.mark.asyncio


now = now_()

repo = TodoRepository(None, None)

valid_db_todo_data = {
    "todo_id": 1,
    "owner": "bob",
    "status": TodoStatus.ACTIVE,
    "created_at": now,
    "updated_at": now,
    "tasks": None,
}
invalid_db_todo_data = {
    "todo_id": "INVALID",
    "owner": "bob",
    "status": TodoStatus.ACTIVE,
    "created_at": now,
    "updated_at": now,
    "tasks": None,
}
valid_db_task_data = {
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
valid_db_task = TaskRow(**valid_db_task_data)
valid_db_todo_data["tasks"] = (valid_db_task for _ in range(3))
valid_db_todo = TodoRow(**valid_db_todo_data)
invalid_db_todo = TodoRow(**invalid_db_todo_data)


@patch.object(TodoRepository, "fetch_one", return_value=valid_db_todo)
async def test_get_one_valid_request(mock: AsyncMock):
    todo_id, prefetch = 1, 7
    res = await TodoService(repo).get_one(
        todo_id=todo_id,
        prefetch_tasks=prefetch,
    )

    mock.assert_awaited_once_with(todo_id, prefetch_tasks=prefetch)
    assert Todo.model_validate(res)


@pytest.mark.xfail(strict=True, raises=BadRequest)
@patch.object(TodoRepository, "fetch_one")
async def test_get_one_invalid_todo_id(_):
    await TodoService(repo).get_one(todo=-1)


@pytest.mark.xfail(strict=True, raises=BadRequest)
@patch.object(TodoRepository, "fetch_one")
async def test_get_one_invalid_prefetch(_):
    await TodoService(repo).get_one(todo_id=1, prefetch_tasks=-1)


@pytest.mark.xfail(strict=True, raises=BadRequest)
@patch.object(TodoRepository, "fetch_one")
async def test_get_one_extra_arg(_):
    await TodoService(repo).get_one(todo_id=1, extra="extra")


@patch.object(TodoRepository, "fetch_one", return_value=None)
async def test_get_one_empty_db_reponse(mock):
    todo_id, default_prefetch = 1, 0
    res = await TodoService(repo).get_one(
        todo_id=todo_id,
        prefetch_tasks=default_prefetch,
    )

    mock.assert_awaited_once_with(todo_id, prefetch_tasks=default_prefetch)
    assert res is None


@pytest.mark.xfail(strict=True, raises=BadResponse)
@patch.object(TodoRepository, "fetch_one", return_value=invalid_db_todo)
async def test_get_one_invalid_db_response(_):
    await TodoService(repo).get_one(todo_id=1)


async def test_get_many_valid_request():
    limit, offset = 20, 10
    filters = {
        "todo_id": [1, 324, 44],
        "owner": ["bob", "alice", "helen"],
        "status": [TodoStatus.ACTIVE, TodoStatus.INACTIVE],
        "created_at": [now, now],
        "updated_at": [now],
    }
    db_response = (valid_db_todo for _ in range(3))

    with patch.object(
        TodoRepository, "fetch_many", return_value=db_response
    ) as mk:
        res = await TodoService(repo).get_many(
            limit=limit, offset=offset, filters=filters
        )

    mk.assert_awaited_once_with(limit=limit, offset=offset, filters=filters)
    assert isinstance(res, list)
    assert all(Todo.model_validate(todo) for todo in res)


@pytest.mark.xfail(strict=True, raises=BadRequest)
@patch.object(TodoRepository, "fetch_many")
async def test_get_many_invalid_limit(_):
    await TodoService(repo).get_many(limit=-20)


@pytest.mark.xfail(strict=True, raises=BadRequest)
@patch.object(TodoRepository, "fetch_many")
async def test_get_many_invalid_offset(_):
    await TodoService(repo).get_many(offset=-20)


@pytest.mark.xfail(strict=True, raises=BadRequest)
@patch.object(TodoRepository, "fetch_many")
async def test_get_many_invalid_filters(_):
    filters = {
        "todo_id": [1, 324, 44],
        "owner": "helen",
        "status": [TodoStatus.ACTIVE, TodoStatus.INACTIVE],
        "created_at": [now, now],
        "updated_at": [now],
    }
    await TodoService(repo).get_many(filters=filters)


async def test_get_many_empty_db_response():
    def_offset, def_filters = 0, None
    db_response = (i for i in [])

    with patch.object(
        TodoRepository, "fetch_many", return_values=db_response
    ) as mk:
        res = await TodoService(repo).get_many()

    mk.assert_awaited_once_with(
        limit=DEFAULT_LIMIT, offset=def_offset, filters=def_filters
    )
    assert res == []


@pytest.mark.xfail(strict=True, raises=BadResponse)
async def test_get_many_invalid_db_response():
    db_response = (invalid_db_todo for _ in range(3))

    with patch.object(TodoRepository, "fetch_many", return_value=db_response):
        await TodoService(repo).get_many()


@patch.object(TodoRepository, "insert_one", return_value=valid_db_todo)
async def test_create_valid_complete_payload(mock: AsyncMock):
    payload = {"owner": "bob", "status": TodoStatus.INACTIVE}
    res = await TodoService(repo).create(**payload)
    mock.assert_awaited_once_with(**payload)
    assert Todo.model_validate(res)


@patch.object(TodoRepository, "insert_one", return_value=valid_db_todo)
async def test_create_valid_parial_payload(mock: AsyncMock):
    payload = {"owner": "bob"}
    res = await TodoService(repo).create(**payload)
    mock.assert_awaited_once_with(**payload, status=TodoStatus.ACTIVE)
    assert Todo.model_validate(res)


@pytest.mark.xfail(strict=True, raises=BadRequest)
@patch.object(TodoRepository, "insert_one")
async def test_create_invalid_status(_):
    payload = {"owner": "bob", "status": "HELLO!"}
    await TodoService(repo).create(**payload)


@pytest.mark.xfail(strict=True, raises=BadRequest)
@patch.object(TodoRepository, "insert_one")
async def test_create_missing_required_owner_arg(_):
    payload = {"status": TodoStatus.INACTIVE}
    await TodoService(repo).create(**payload)


@patch.object(TodoRepository, "insert_one", return_value=None)
async def test_create_empty_db_response(mock: AsyncMock):
    payload = {"owner": "bob"}
    res = await TodoService(repo).create(**payload)

    mock.assert_awaited_once()
    assert res is None


@pytest.mark.xfail(strict=True, raises=BadResponse)
@patch.object(TodoRepository, "insert_one", return_value=invalid_db_todo)
async def test_create_invalid_db_response(_):
    payload = {"owner": "bob"}
    await TodoService(repo).create(**payload)


@patch.object(TodoRepository, "update_one", return_value=valid_db_todo)
async def test_update_valid_complete_payload(mock: AsyncMock):
    todo_id = 1
    payload = {
        "owner": "bob",
        "status": TodoStatus.ACTIVE,
        "created_at": now,
        "updated_at": now,
    }

    res = await TodoService(repo).update(todo_id=todo_id, payload=payload)

    mock.assert_awaited_once_with(todo_id, payload)
    assert Todo.model_validate(res)


@patch.object(TodoRepository, "update_one", return_value=valid_db_todo)
async def test_update_valid_partial_payload(mock: AsyncMock):
    todo_id = 1
    payload = {
        "status": TodoStatus.ACTIVE,
        "created_at": now,
    }

    res = await TodoService(repo).update(todo_id=todo_id, payload=payload)

    mock.assert_awaited_once_with(todo_id, payload)
    assert Todo.model_validate(res)


@pytest.mark.xfail(strict=True, raises=BadRequest)
@patch.object(TodoRepository, "update_one")
async def test_update_empty_payload(_):
    await TodoService(repo).update(todo_id=1, payload={})


@pytest.mark.xfail(strict=True, raises=BadRequest)
@patch.object(TodoRepository, "update_one")
async def test_update_invalid_created_at(_):
    await TodoService(repo).update(
        todo_id=1, payload={"created_at": "-12345f5"}
    )


@pytest.mark.xfail(strict=True, raises=BadRequest)
@patch.object(TodoRepository, "update_one")
async def test_update_invalid_status(_):
    await TodoService(repo).update(todo_id=1, payload={"status": "INVALID"})


@pytest.mark.xfail(strict=True, raises=BadRequest)
@patch.object(TodoRepository, "update_one")
async def test_update_extra_argument(_):
    await TodoService(repo).update(todo_id=1, payload={"extra": "extra"})


@patch.object(TodoRepository, "update_one", return_value=None)
async def test_update_empty_db_response(mock: AsyncMock):
    todo_id = 1
    update_data = {"status": TodoStatus.ACTIVE}

    res = await TodoService(repo).update(todo_id=todo_id, payload=update_data)

    mock.assert_awaited_once_with(todo_id, update_data)
    assert res is None


@pytest.mark.xfail(strict=True, raises=BadResponse)
@patch.object(TodoRepository, "update_one", return_value=invalid_db_todo)
async def test_update_invalid_db_response(_):
    await TodoService(repo).update(todo_id=1, payload={"owner": "owner"})


@patch.object(TodoRepository, "delete_one", return_value=1)
async def test_delete_valid_todo_id(mock: AsyncMock):
    todo_id = 1
    res = await TodoService(repo).delete(todo_id=todo_id)

    mock.assert_awaited_once_with(todo_id)
    assert res is True


@pytest.mark.xfail(strict=True, raises=BadRequest)
@patch.object(TodoRepository, "delete_one")
async def test_delete_invalid_todo_id(_):
    await TodoService(repo).delete(todo_id="hello")


@patch.object(TodoRepository, "delete_one", return_value=None)
async def test_delete_empty_db_response(mock: AsyncMock):
    todo_id = 1
    res = await TodoService(repo).delete(todo_id=todo_id)

    mock.assert_awaited_once_with(todo_id)
    assert res is False
