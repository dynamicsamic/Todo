from unittest.mock import AsyncMock, patch

import pytest

from src.data.repository import TaskRepository
from src.data.result import TaskRow
from src.domain.models import Task
from src.domain.types import TaskPriority, TaskStatus
from src.service.task import TaskService
from src.service.validation import BadRequest, BadResponse
from src.settings import settings
from src.utils import now as now_

pytestmark = pytest.mark.asyncio

DEFAULT_LIMIT = settings.DEFAULT_PAGE_LIMIT

now = now_()

repo = TaskRepository(None, None)

valid_db_task_data = {
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
invalid_db_task_data = {
    "task_id": 1,
    "brief": "brief1",
    "todo_id": "INVALID TODO_ID",
    "contents": None,
    "status": TaskStatus.COMPLETE,
    "priority": TaskPriority.HIGH,
    "category": "category2",
    "due": now,
    "created_at": now,
    "updated_at": now,
}

valid_db_task = TaskRow(**valid_db_task_data)
invalid_db_task = TaskRow(**invalid_db_task_data)


@patch.object(TaskRepository, "fetch_one", return_value=valid_db_task)
async def test_get_one_valid_request(mock: AsyncMock):
    task_id = 1
    res = await TaskService(repo).get_one(task_id=task_id)

    mock.assert_awaited_once_with(task_id)
    assert Task.model_validate(res)
    assert res.model_dump() == valid_db_task_data


@pytest.mark.xfail(strict=True, raises=BadRequest)
@patch.object(TaskRepository, "fetch_one")
async def test_get_one_extra_arg(_):
    await TaskService(repo).get_one(task_id=1, extra="extra")


@pytest.mark.xfail(strict=True, raises=BadRequest)
@patch.object(TaskRepository, "fetch_one")
async def test_get_one_invalid_task_id(_):
    await TaskService(repo).get_one(task_id=-1)


@patch.object(TaskRepository, "fetch_one", return_value=None)
async def test_get_one_empty_db_response(mock: AsyncMock):
    task_id = 1
    res = await TaskService(repo).get_one(task_id=1)

    mock.assert_awaited_once_with(task_id)
    assert res is None


@pytest.mark.xfail(strict=True, raises=BadResponse)
@patch.object(TaskRepository, "fetch_one", return_value=invalid_db_task)
async def test_get_one_invalid_db_response(_):
    await TaskService(repo).get_one(task_id=1)


async def test_get_many_valid_request():
    limit = 15
    default_offset = 0
    filters = {
        "task_id": [1, 2, 3, 4, 5, 6],
        "todo_id": [54, 21, 777, 1],
        "brief": ["brief1", "brief2"],
        "category": ["cat1"],
        "status": [TaskStatus.COMPLETE, TaskStatus.PENDING],
        "priority": [TaskPriority.HIGH],
        "due": [now, now],
        "created_at": [now],
    }
    db_response = (valid_db_task for _ in range(5))

    with patch.object(
        TaskRepository, "fetch_many", return_value=db_response
    ) as mock:
        res = await TaskService(repo).get_many(limit=limit, filters=filters)

    mock.assert_awaited_once_with(
        limit=limit, offset=default_offset, filters=filters
    )
    assert isinstance(res, list)
    assert all(Task.model_validate(task) for task in res)


@pytest.mark.xfail(strict=True, raises=BadRequest)
@patch.object(TaskRepository, "fetch_many")
async def test_get_many_invalid_limit(_):
    await TaskService(repo).get_many(limit=-15)


@pytest.mark.xfail(strict=True, raises=BadRequest)
@patch.object(TaskRepository, "fetch_many")
async def test_get_many_invalid_offset(_):
    await TaskService(repo).get_many(offset=-15)


@pytest.mark.xfail(strict=True, raises=BadRequest)
@patch.object(TaskRepository, "fetch_many")
async def test_get_many_invalid_filters(_):
    filters = {
        "task_id": [1, 2, 3, 4, 5, 6],
        "todo_id": [54, 21, 777, 1],
        "brief": ["brief1", "brief2"],
        "category": ["cat1"],
        "status": ["INVALID_STATUS1", "INVALID_STATUS3"],
    }
    await TaskService(repo).get_many(filters=filters)


async def test_get_many_empty_db_response():
    default_offset = 0
    filters = None
    db_response = (i for i in [])

    with patch.object(
        TaskRepository, "fetch_many", return_value=db_response
    ) as mock:
        res = await TaskService(repo).get_many()

    mock.assert_awaited_once_with(
        limit=DEFAULT_LIMIT, offset=default_offset, filters=filters
    )
    assert res == []


@pytest.mark.xfail(strict=True, raises=BadResponse)
async def test_get_many_invalid_db_response():
    db_response = (invalid_db_task for _ in range(5))

    with patch.object(TaskRepository, "fetch_many", return_value=db_response):
        await TaskService(repo).get_many()


@patch.object(TaskRepository, "insert_one", return_value=valid_db_task)
async def test_create_valid_complete_payload(mock: AsyncMock):
    task_data = {
        "brief": "brief1",
        "todo_id": 1,
        "contents": "contents",
        "status": TaskStatus.COMPLETE,
        "priority": TaskPriority.HIGH,
        "category": "category2",
        "due": now,
    }
    res = await TaskService(repo).create(**task_data)

    mock.assert_awaited_once_with(**task_data)
    assert Task.model_validate(res)


@patch.object(TaskRepository, "insert_one", return_value=valid_db_task)
async def test_create_valid_partial_payload(mock: AsyncMock):
    required_data = {
        "brief": "brief1",
        "todo_id": 1,
        "category": "category2",
    }
    default_data = {
        "status": TaskStatus.PENDING,
        "priority": TaskPriority.LOW,
    }
    res = await TaskService(repo).create(**required_data)

    # check default due is set as `now +1 day`, when due not set by client
    due_set_by_service = mock.await_args.kwargs.pop("due")
    assert (due_set_by_service - now).days == 1
    mock.assert_awaited_once_with(**required_data, **default_data)
    assert Task.model_validate(res)


@pytest.mark.xfail(strict=True, raises=BadRequest)
@patch.object(TaskRepository, "insert_one")
async def test_create_invalid_todo_id(_):
    data = {
        "brief": "brief1",
        "todo_id": -12,
        "category": "category2",
    }
    await TaskService(repo).create(**data)


@pytest.mark.xfail(strict=True, raises=BadRequest)
@patch.object(TaskRepository, "insert_one")
async def test_create_invalid_status(_):
    data = {
        "brief": "brief1",
        "todo_id": 12,
        "category": "category2",
        "status": "INVALID",
    }
    await TaskService(repo).create(**data)


@pytest.mark.xfail(strict=True, raises=BadRequest)
@patch.object(TaskRepository, "insert_one")
async def test_create_missing_required_brief_arg(_):
    data = {
        "todo_id": 12,
        "category": "category2",
        "status": TaskStatus.COMPLETE,
    }
    await TaskService(repo).create(**data)


@pytest.mark.xfail(strict=True, raises=BadRequest)
@patch.object(TaskRepository, "insert_one")
async def test_create_extra_argument(_):
    data = {
        "brief": "brief1",
        "todo_id": 1,
        "category": "category2",
        "extra": "extra",
    }
    await TaskService(repo).create(**data)


@patch.object(TaskRepository, "insert_one", return_value=None)
async def test_create_empty_db_response(mock: AsyncMock):
    data = {
        "brief": "brief1",
        "todo_id": 1,
        "category": "category2",
    }
    res = await TaskService(repo).create(**data)

    mock.assert_awaited_once()
    assert res is None


@pytest.mark.xfail(strict=True, raises=BadResponse)
@patch.object(TaskRepository, "insert_one", return_value=invalid_db_task)
async def test_create_invalid_db_response(_):
    data = {
        "brief": "brief1",
        "todo_id": 1,
        "category": "category2",
    }
    await TaskService(repo).create(**data)


@patch.object(TaskRepository, "update_one", return_value=valid_db_task)
async def test_update_valid_complete_payload(mock: AsyncMock):
    task_id = 1
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
    res = await TaskService(repo).update(task_id=task_id, payload=payload)

    mock.assert_awaited_once_with(task_id, payload)
    assert Task.model_validate(res)


@patch.object(TaskRepository, "update_one", return_value=valid_db_task)
async def test_update_valid_partial_payload(mock: AsyncMock):
    task_id = 1
    payload = {
        "brief": "brief1",
        "contents": "contents",
        "status": TaskStatus.COMPLETE,
        "category": "category2",
        "due": now,
    }
    res = await TaskService(repo).update(task_id=task_id, payload=payload)

    mock.assert_awaited_once_with(task_id, payload)
    assert Task.model_validate(res)


@pytest.mark.xfail(strict=True, raises=BadRequest)
@patch.object(TaskRepository, "update_one")
async def test_update_empty_payload(_):
    await TaskService(repo).update(task_id=1, payload={"brief": None})


@pytest.mark.xfail(strict=True, raises=BadRequest)
@patch.object(TaskRepository, "update_one")
async def test_update_invalid_created_at(_):
    await TaskService(repo).update(task_id=1, payload={"created_at": "134v8"})


@pytest.mark.xfail(strict=True, raises=BadRequest)
@patch.object(TaskRepository, "update_one")
async def test_update_invalid_task_priority(_):
    await TaskService(repo).update(task_id=1, payload={"priority": "INV"})


@pytest.mark.xfail(strict=True, raises=BadRequest)
@patch.object(TaskRepository, "update_one")
async def test_update_extra_argument(_):
    await TaskService(repo).update(task_id=1, payload={"extra": "extra"})


@patch.object(TaskRepository, "update_one", return_value=None)
async def test_update_empty_db_response(mock: AsyncMock):
    task_id = 1
    payload = {"brief": "brief1"}
    res = await TaskService(repo).update(task_id=task_id, payload=payload)

    mock.assert_awaited_once_with(task_id, payload)
    assert res is None


@pytest.mark.xfail(strict=True, raises=BadResponse)
@patch.object(TaskRepository, "update_one", return_value=invalid_db_task)
async def test_update_invalid_db_response(_):
    await TaskService(repo).update(task_id=1, payload={"brief": "brief"})


@patch.object(TaskRepository, "delete_one", return_value=1)
async def test_delete_valid_task_id(mock: AsyncMock):
    task_id = 1
    res = await TaskService(repo).delete(task_id=task_id)

    mock.assert_awaited_once_with(task_id)
    assert res is True


@pytest.mark.xfail(strict=True, raises=BadRequest)
@patch.object(TaskRepository, "delete_one")
async def test_delete_invalid_task_id(_):
    await TaskService(repo).delete(task_id=-1)


@patch.object(TaskRepository, "delete_one", return_value=None)
async def test_delete_empty_db_response(mock: AsyncMock):
    task_id = 1
    res = await TaskService(repo).delete(task_id=task_id)

    mock.assert_awaited_once_with(task_id)
    assert res is False
