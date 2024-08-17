import pytest_asyncio

from main import app
from src.data.db import load_tasks, load_todos

TODO_SAMPLE_SIZE = 1000
TASK_SAMPLE_SIZE = 1500


@pytest_asyncio.fixture(scope="module", autouse=True)
async def test_client():
    async with app.test_app() as test_app:
        async with app.db_pool.acquire() as con:
            await load_todos(con, TODO_SAMPLE_SIZE)
            await load_tasks(con, TASK_SAMPLE_SIZE)
        yield test_app.test_client()

        # async with app.db_pool.acquire() as con:
        # await cleanup_table(con, 'todos')


# async def test_foo(test_app):
# test_client = test_app.test_client()


# @pytest_asyncio.fixture(scope="module", autouse=True)
# async def test_client(test_app):
#     yield test_app.test_client()
