import datetime as dt
from typing import Generator

import asyncpg
import pytest
import pytest_asyncio

from src.data.db import (
    apply_migration,
    check_db_created,
    drop_db,
    get_connection_url,
    load_all,
)
from src.data.repository import TaskRepository, TodoRepository
from src.data.result import TaskRow, TodoRow
from src.domain.types import TaskPriority, TaskStatus, TodoStatus
from src.utils import now
from tests.conftest import (
    TASK_SAMPLE_SIZE,
    TODO_SAMPLE_SIZE,
)

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(scope="module")
async def prepare_db():
    await check_db_created()
    await apply_migration("_000_initial")
    await load_all(TODO_SAMPLE_SIZE, TASK_SAMPLE_SIZE)
    yield
    await drop_db()


@pytest_asyncio.fixture(scope="module")
async def pool(prepare_db):
    pool = await asyncpg.create_pool(get_connection_url())
    yield pool
    await pool.close()


class TestTodoRepository:
    pool: asyncpg.Pool = None
    new_todo_id: int = None

    @pytest_asyncio.fixture(autouse=True, scope="module")
    async def setup(self, pool):
        self.__class__.pool = pool

    def get_todo_id(self) -> int:
        return self.__class__.new_todo_id or TODO_SAMPLE_SIZE

    async def test_fetch_todos_without_arguments_uses_default_limit(self):
        async with self.pool.acquire() as con:
            repo = TodoRepository(con, self.pool)
            res = await repo.fetch_many()

        assert isinstance(res, Generator)
        todos = list(res)
        assert len(todos) == TodoRepository.LIMIT
        assert all(isinstance(todo, TodoRow) for todo in todos)

    async def test_fetch_todos_with_custom_limit(self):
        limit = 3

        async with self.pool.acquire() as con:
            repo = TodoRepository(con, self.pool)
            res = await repo.fetch_many(limit=limit)

        todos = list(res)
        assert len(todos) == limit
        assert all(isinstance(todo, TodoRow) for todo in todos)

    async def test_fetch_todos_with_custom_offset(self):
        offset = 2

        async with self.pool.acquire() as con:
            repo = TodoRepository(con, self.pool)
            res = await repo.fetch_many(offset=offset)

        todos = list(res)
        assert len(todos) == TodoRepository.LIMIT
        assert all(todo.todo_id > offset for todo in todos)

    async def test_fetch_todos_with_custom_ordering(self):
        async with self.pool.acquire() as con:
            repo = TodoRepository(con, self.pool)
            res = await repo.fetch_many(order_by=["todo_id DESC"])

        todos = list(res)
        assert all(
            todos[i].todo_id > todos[i + 1].todo_id
            for i in range(len(todos) - 1)
        )

    async def test_fetch_todos_with_one_filter_single_value(self):
        filters = {"todo_id": [1]}

        async with self.pool.acquire() as con:
            repo = TodoRepository(con, self.pool)
            res = await repo.fetch_many(filters=filters)

        todos = list(res)
        assert len(todos) == len(filters["todo_id"])
        todo = todos[0]
        todo.todo_id == filters["todo_id"][0]

    async def test_fetch_todos_with_one_filter_multiple_values(self):
        filters = {"todo_id": [1, 2, 3]}

        async with self.pool.acquire() as con:
            repo = TodoRepository(con, self.pool)
            res = await repo.fetch_many(filters=filters)

        todos = list(res)
        assert len(todos) == len(filters["todo_id"])
        assert all(
            todo.todo_id == todo_id
            for todo, todo_id in zip(todos, filters["todo_id"])
        )

    async def test_fetch_todos_with_multiple_filters_unique_combination(self):
        filters = {"todo_id": [1, 2, 3], "owner": ["todo1", "invalid"]}

        async with self.pool.acquire() as con:
            repo = TodoRepository(con, self.pool)
            res = await repo.fetch_many(filters=filters)

        todos = list(res)
        assert len(todos) == 1
        todo = todos[0]
        assert todo.owner == filters["owner"][0]

    async def test_fetch_todos_with_multiple_filters_generic_combination(self):
        filters = {"todo_id": [1, 2, 3], "status": [TodoStatus.ACTIVE]}

        async with self.pool.acquire() as con:
            repo = TodoRepository(con, self.pool)
            res = await repo.fetch_many(limit=10, filters=filters)

        todos = list(res)
        assert all(todo.status == TodoStatus.ACTIVE for todo in todos)

    async def test_fetch_todos_do_not_exist(self):
        async with self.pool.acquire() as con:
            repo = TodoRepository(con, self.pool)
            res = await repo.fetch_many(filters={"todo_id": [-1]})

        assert len(list(res)) == 0

    async def test_fetch_existing_todo_without_prefetch(self):
        todo_id = 1

        async with self.pool.acquire() as con:
            repo = TodoRepository(con, self.pool)
            todo = await repo.fetch_one(todo_id)

        assert isinstance(todo, TodoRow)
        assert todo.tasks is None

        assert todo.owner.startswith("todo")
        assert todo.todo_id == todo_id
        assert todo.created_at is not None
        assert todo.updated_at is not None

    async def test_fetch_existing_todo_with_prefetch(self):
        todo_id = 1
        prefetch = 5

        async with self.pool.acquire() as con:
            repo = TodoRepository(con, self.pool)
            todo = await repo.fetch_one(todo_id, prefetch)

        assert isinstance(todo, TodoRow)
        assert isinstance(todo.tasks, Generator)

        assert todo.todo_id == todo_id
        tasks = list(todo.tasks)
        assert len(tasks) == prefetch
        assert all(isinstance(task, TaskRow) for task in tasks)
        assert all(task.todo_id == todo_id for task in tasks)

    async def test_fetch_todo_does_not_exist(self):
        async with self.pool.acquire() as con:
            repo = TodoRepository(con, self.pool)
            todo = await repo.fetch_one(-1, 5)

        assert todo is None

    async def test_insert_todo_with_valid_args_without_tasks(self):
        async with self.pool.acquire() as con:
            initial_count = await con.fetchval(
                "SELECT count(todo_id) FROM todos"
            )

        data = {"owner": "helen", "status": TodoStatus.INACTIVE}
        async with self.pool.acquire() as con:
            repo = TodoRepository(con, self.pool)
            todo = await repo.insert_one(**data)

        assert isinstance(todo, TodoRow)
        assert todo.tasks is None
        assert todo.owner == data["owner"]
        assert todo.status == data["status"]
        assert todo.todo_id > 0
        assert isinstance(todo.created_at, dt.datetime)
        assert isinstance(todo.updated_at, dt.datetime)

        self.__class__.new_todo_id = todo.todo_id

        async with self.pool.acquire() as con:
            current_count = await con.fetchval(
                "SELECT count(todo_id) FROM todos"
            )

        assert current_count == initial_count + 1

    @pytest.mark.xfail(strict=True)
    async def test_insert_todo_invalid_column_name(self):
        invalid_data = {"invalid": "helen", "status": TodoStatus.INACTIVE}
        async with self.pool.acquire() as con:
            repo = TodoRepository(con, self.pool)
            await repo.insert_one(**invalid_data)

    @pytest.mark.xfail(strict=True)
    async def test_insert_todo_invalid_column_type(self):
        invalid_data = {"owner": [], "status": TodoStatus.INACTIVE}
        async with self.pool.acquire() as con:
            repo = TodoRepository(con, self.pool)
            await repo.insert_one(**invalid_data)

    async def test_update_existing_todo_with_valid_data(self):
        todo_id = self.get_todo_id()

        async with self.pool.acquire() as con:
            repo = TodoRepository(con, self.pool)
            original_todo = await repo.fetch_one(todo_id)

        status = (
            TodoStatus.INACTIVE
            if original_todo.status == TodoStatus.ACTIVE
            else TodoStatus.ACTIVE
        )
        updated_at = now()
        update_data = {
            "owner": "steve",
            "status": status,
            "updated_at": updated_at,
        }

        async with self.pool.acquire() as con:
            repo = TodoRepository(con, self.pool)
            updated_todo = await repo.update_one(todo_id, update_data)

        assert updated_todo.todo_id == original_todo.todo_id
        assert (
            updated_todo.owner == update_data["owner"] != original_todo.owner
        )
        assert (
            updated_todo.status
            == update_data["status"]
            != original_todo.status
        )
        assert (
            updated_todo.updated_at
            == update_data["updated_at"]
            != original_todo.updated_at
        )

        # rollback the update
        rollback_data = {
            "owner": original_todo.owner,
            "status": original_todo.status,
            "updated_at": original_todo.updated_at,
        }
        async with self.pool.acquire() as con:
            repo = TodoRepository(con, self.pool)
            await repo.update_one(todo_id, rollback_data)

    async def test_update_todo_does_not_exist(self):
        update_data = {"owner": "steve"}

        async with self.pool.acquire() as con:
            repo = TodoRepository(con, self.pool)
            res = await repo.update_one(-1, update_data)

        assert res is None

    @pytest.mark.xfail(strict=True)
    async def test_update_existing_todo_with_invalid_column_name(self):
        invalid_data = {"Invlaid": "steve", "status": TodoStatus.ACTIVE}

        async with self.pool.acquire() as con:
            repo = TodoRepository(con, self.pool)
            await repo.update_one(1, invalid_data)

    @pytest.mark.xfail(strict=True)
    async def test_update_existing_todo_with_invalid_column_type(self):
        invalid_data = {"owner": [], "status": TodoStatus.ACTIVE}

        async with self.pool.acquire() as con:
            repo = TodoRepository(con, self.pool)
            await repo.update_one(1, invalid_data)

    @pytest.mark.xfail(strict=True)
    async def test_update_existing_todo_with_empty_data(self):
        async with self.pool.acquire() as con:
            repo = TodoRepository(con, self.pool)
            await repo.update_one(1, {})

    async def test_delete_existing_todo(self):
        from src.data.repository import TaskRepository

        task_data = {
            "brief": "unit_insert_test_1",
            "category": "unit_insert_test_1",
            "due": now(),
        }

        todo_id = self.get_todo_id()
        async with self.pool.acquire() as con:
            repo = TaskRepository(con, self.pool)
            task = await repo.insert_one(**task_data, todo_id=todo_id)

        assert task.todo_id == todo_id

        async with self.pool.acquire() as con:
            repo = TodoRepository(con, self.pool)
            todo = await repo.fetch_one(todo_id=todo_id, prefetch_tasks=20)

        assert len(list(todo.tasks)) == 1

        async with self.pool.acquire() as con:
            repo = TodoRepository(con, self.pool)
            res = await repo.delete_one(todo_id)

        assert res == todo_id

        async with self.pool.acquire() as con:
            repo = TodoRepository(con, self.pool)
            todo = await repo.fetch_one(todo_id=todo_id, prefetch_tasks=20)

        assert todo is None

        async with self.pool.acquire() as con:
            repo = TaskRepository(con, self.pool)
            task = await repo.fetch_one(task.task_id)

        assert task is None

    async def test_delete_todo_does_not_exist(self):
        todo_id = -1

        async with self.pool.acquire() as con:
            repo = TodoRepository(con, self.pool)
            res = await repo.delete_one(todo_id)

        assert res is None

    @pytest.mark.skip("Not used in production yet")
    async def test_todo_estimate(self):
        async with self.pool.acquire() as con:
            repo = TodoRepository(con, self.pool)
            estimate = await repo.estimate()

        async with self.pool.acquire() as con:
            count = await con.fetchval("SELECT count(todo_id) FROM todos")

        assert estimate == count


class TestTaskRepository:
    pool: asyncpg.Pool = None
    new_task_id: int = None

    @pytest_asyncio.fixture(autouse=True, scope="module")
    async def setup(self, pool):
        self.__class__.pool = pool

    def get_task_id(self) -> int:
        return self.new_task_id or TASK_SAMPLE_SIZE

    async def test_insert_task_with_valid_data(self):
        due = now()
        data = {
            "brief": "biref1",
            "todo_id": 1,
            "category": "category2",
            "due": due,
            "contents": "contents2",
            "status": TaskStatus.COMPLETE,
            "priority": TaskPriority.HIGH,
        }

        async with self.pool.acquire() as con:
            initial_count = await con.fetchval(
                "SELECT count(task_id) FROM tasks"
            )

        async with self.pool.acquire() as con:
            repo = TaskRepository(con, self.pool)
            task = await repo.insert_one(**data)

        assert isinstance(task, TaskRow)
        assert task.task_id > 0
        assert task.brief == data["brief"]
        assert task.todo_id == data["todo_id"]
        assert task.category == data["category"]
        assert task.due == data["due"]
        assert task.contents == data["contents"]
        assert task.status == data["status"]
        assert task.priority == data["priority"]

        async with self.pool.acquire() as con:
            current_count = await con.fetchval(
                "SELECT count(task_id) FROM tasks"
            )

        assert current_count == initial_count + 1

        self.__class__.new_task_id = task.task_id

    @pytest.mark.xfail(strict=True)
    async def test_insert_task_with_missing_column(self):
        no_due_data = {
            "brief": "biref1",
            "todo_id": 1,
            "category": "category2",
            "contents": "contents2",
            "status": TaskStatus.COMPLETE,
            "priority": TaskPriority.HIGH,
        }

        async with self.pool.acquire() as con:
            repo = TaskRepository(con, self.pool)
            await repo.insert_one(**no_due_data)

    @pytest.mark.xfail(strict=True)
    async def test_insert_task_with_invalid_column_name(self):
        due = now()
        invlaid_category_col = {
            "brief": "biref1",
            "todo_id": 1,
            "invalid": "category2",
            "due": due,
            "contents": "contents2",
            "status": TaskStatus.COMPLETE,
            "priority": TaskPriority.HIGH,
        }

        async with self.pool.acquire() as con:
            repo = TaskRepository(con, self.pool)
            await repo.insert_one(**invlaid_category_col)

    @pytest.mark.xfail(strict=True)
    async def test_insert_task_with_invalid_column_type(self):
        due = now()
        invlaid_todo_id_type = {
            "brief": "biref1",
            "todo_id": [],
            "category": "category2",
            "due": due,
            "contents": "contents2",
            "status": TaskStatus.COMPLETE,
            "priority": TaskPriority.HIGH,
        }

        async with self.pool.acquire() as con:
            repo = TaskRepository(con, self.pool)
            await repo.insert_one(**invlaid_todo_id_type)

    async def test_fetch_existing_task(self):
        task_id = 1

        async with self.pool.acquire() as con:
            repo = TaskRepository(con, self.pool)
            task = await repo.fetch_one(task_id)

        assert isinstance(task, TaskRow)
        assert task.task_id == task_id
        assert task.todo_id > 0
        assert task.brief
        assert task.category
        assert task.due
        assert task.status
        assert task.priority
        assert task.created_at
        assert task.updated_at

    async def test_fetch_task_does_not_exist(self):
        async with self.pool.acquire() as con:
            repo = TaskRepository(con, self.pool)
            task = await repo.fetch_one(-1)

        assert task is None

    async def test_fetch_tasks_without_arguments_uses_default_limit(self):
        async with self.pool.acquire() as con:
            repo = TaskRepository(con, self.pool)
            res = await repo.fetch_many()

        assert isinstance(res, Generator)
        tasks = list(res)
        assert len(tasks) == TaskRepository.LIMIT
        assert all(isinstance(task, TaskRow) for task in tasks)

    async def test_fetch_tasks_with_custom_limit(self):
        limit = 3

        async with self.pool.acquire() as con:
            repo = TaskRepository(con, self.pool)
            res = await repo.fetch_many(limit=limit)

        tasks = list(res)
        assert len(tasks) == limit
        assert all(isinstance(task, TaskRow) for task in tasks)

    async def test_fetch_tasks_with_custom_offset(self):
        offset = 2

        async with self.pool.acquire() as con:
            repo = TaskRepository(con, self.pool)
            res = await repo.fetch_many(offset=offset)

        tasks = list(res)
        assert len(tasks) == TaskRepository.LIMIT
        assert all(task.task_id > offset for task in tasks)

    async def test_fetch_tasks_with_custom_ordering(self):
        async with self.pool.acquire() as con:
            repo = TaskRepository(con, self.pool)
            res = await repo.fetch_many(order_by=["task_id DESC"])

        tasks = list(res)
        assert all(
            tasks[i].task_id > tasks[i + 1].task_id
            for i in range(len(tasks) - 1)
        )

    async def test_fetch_tasks_with_one_filter_single_value(self):
        filters = {"task_id": [1]}

        async with self.pool.acquire() as con:
            repo = TaskRepository(con, self.pool)
            res = await repo.fetch_many(filters=filters)

        tasks = list(res)
        assert len(tasks) == len(filters["task_id"])
        task = tasks[0]
        task.task_id == filters["task_id"][0]

    async def test_fetch_tasks_with_one_filter_multiple_values(self):
        filters = {"task_id": [1, 2, 3]}

        async with self.pool.acquire() as con:
            repo = TaskRepository(con, self.pool)
            res = await repo.fetch_many(filters=filters)

        tasks = list(res)
        assert len(tasks) == len(filters["task_id"])
        assert all(
            task.task_id == task_id
            for task, task_id in zip(tasks, filters["task_id"])
        )

    async def test_fetch_tasks_with_multiple_filters_unique_combination(self):
        filters = {
            "task_id": [1],
            "status": [
                TaskStatus.COMPLETE,
                TaskStatus.PENDING,
                TaskStatus.POSTPONED,
            ],
        }

        async with self.pool.acquire() as con:
            repo = TaskRepository(con, self.pool)
            res = await repo.fetch_many(filters=filters)

        tasks = list(res)
        assert len(tasks) == 1
        task = tasks[0]
        assert task.task_id == filters["task_id"][0]

    async def test_fetch_tasks_with_multiple_filters_generic_combination(self):
        filters = {
            "task_id": [1, 2, 3],
            "status": [TaskStatus.COMPLETE],
            "todo_id": [1, 2, 3],
        }

        async with self.pool.acquire() as con:
            repo = TaskRepository(con, self.pool)
            res = await repo.fetch_many(limit=10, filters=filters)

        tasks = list(res)
        assert all(task.status == TaskStatus.COMPLETE for task in tasks)

    async def test_fetch_tasks_do_not_exist(self):
        async with self.pool.acquire() as con:
            repo = TaskRepository(con, self.pool)
            res = await repo.fetch_many(filters={"task_id": [-1]})

        assert len(list(res)) == 0

    async def test_update_existing_task_with_valid_data(self):
        task_id = self.get_task_id()

        async with self.pool.acquire() as con:
            repo = TaskRepository(con, self.pool)
            original_task = await repo.fetch_one(task_id)

        status = None
        if original_task.status == TaskStatus.COMPLETE:
            status = TaskStatus.PENDING
        elif original_task.status == TaskStatus.PENDING:
            status = TaskStatus.POSTPONED
        else:
            status = TaskStatus.COMPLETE

        due = now()
        update_data = {"brief": "test_brief", "status": status, "due": due}

        async with self.pool.acquire() as con:
            repo = TaskRepository(con, self.pool)
            updated_todo = await repo.update_one(task_id, update_data)

        assert updated_todo.todo_id == original_task.todo_id
        assert (
            updated_todo.brief == update_data["brief"] != original_task.brief
        )
        assert (
            updated_todo.status
            == update_data["status"]
            != original_task.status
        )
        assert updated_todo.due == update_data["due"] != original_task.due

        # rollback the update
        rollback_data = {
            "brief": original_task.brief,
            "status": original_task.status,
            "due": original_task.due,
        }
        async with self.pool.acquire() as con:
            repo = TaskRepository(con, self.pool)
            updated_todo = await repo.update_one(task_id, rollback_data)

    async def test_update_task_does_not_exist(self):
        update_data = {"brief": "test_brief"}

        async with self.pool.acquire() as con:
            repo = TaskRepository(con, self.pool)
            res = await repo.update_one(-1, update_data)

        assert res is None

    @pytest.mark.xfail(strict=True)
    async def test_update_existing_task_with_invalid_column_name(self):
        invalid_data = {"Invlaid": "test_bried", "status": TaskStatus.COMPLETE}

        async with self.pool.acquire() as con:
            repo = TaskRepository(con, self.pool)
            await repo.update_one(1, invalid_data)

    @pytest.mark.xfail(strict=True)
    async def test_update_existing_task_with_invalid_column_type(self):
        invalid_data = {"brief": [], "status": TaskStatus.COMPLETE}

        async with self.pool.acquire() as con:
            repo = TaskRepository(con, self.pool)
            await repo.update_one(1, invalid_data)

    @pytest.mark.xfail(strict=True)
    async def test_update_existing_task_with_empty_data(self):
        async with self.pool.acquire() as con:
            repo = TaskRepository(con, self.pool)
            await repo.update_one(1, {})

    async def test_delete_existing_task(self):
        task_id = self.get_task_id()

        async with self.pool.acquire() as con:
            repo = TaskRepository(con, self.pool)
            res = await repo.delete_one(task_id)

        assert res == task_id

        async with self.pool.acquire() as con:
            repo = TaskRepository(con, self.pool)
            task = await repo.fetch_one(task_id)

        assert task is None

    async def test_delete_task_does_not_exist(self):
        task_id = -1

        async with self.pool.acquire() as con:
            repo = TaskRepository(con, self.pool)
            res = await repo.delete_one(task_id)

        assert res is None

    @pytest.mark.skip("Not used in production yet")
    async def test_task_estimate(self):
        async with self.pool.acquire() as con:
            repo = TaskRepository(con, self.pool)
            estimate = await repo.estimate()

        async with self.pool.acquire() as con:
            count = await con.fetchval("SELECT count(task_id) FROM tasks")

        assert estimate == count
