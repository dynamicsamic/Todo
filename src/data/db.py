import importlib
import logging
from typing import Literal

import asyncpg

from src.domain.types import TaskPriority, TaskStatus, TodoStatus
from src.settings import settings
from src.utils import AsyncpgQueryLogger, now, random_choice_enum

logger = logging.getLogger(__name__)

simple_logger = AsyncpgQueryLogger(logger, detailed=False)
detailed_logger = AsyncpgQueryLogger(logger)


def get_connection_url(
    user: str = settings.PG_USER,
    password: str = settings.PG_PASSWORD,
    database: str = settings.PG_DB,
    host: str = settings.PG_HOST,
    port: int = settings.PG_PORT,
) -> str:
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


async def check_db_created(
    user: str = settings.PG_USER,
    password: str = settings.PG_PASSWORD,
    database: str = settings.PG_DB,
    host: str = settings.PG_HOST,
    port: int = settings.PG_PORT,
) -> None:
    logger.info(f"Connecting to database {database}")
    try:
        await asyncpg.connect(get_connection_url(user, password, database, host, port))
    except asyncpg.InvalidCatalogNameError:
        logger.info(
            f"Connection to database {database} FAILED. Connecting "
            f"to default `postgres` database to create {database} db."
        )
        conn = await asyncpg.connect(
            get_connection_url(user, password, "postgres", host, port)
        )
        with conn.query_logger(simple_logger):
            await conn.execute(f"CREATE DATABASE {database};")
            await conn.close()

        logger.info(f"Database {database} created.")


async def apply_migration(
    file: str | None = None, type_: Literal["upgrade", "downgrade"] = "upgrade"
) -> None:
    module = "src.data.migrations"
    if file:
        module = f"{module}.{file}"

    migrations = importlib.import_module(module)

    if file:
        qry = getattr(migrations, type_)
    else:
        migrations = (
            reversed(migrations.__all__) if type_ == "downgrade" else migrations.__all__
        )
        qry = " ".join([getattr(migration, type_) for migration in migrations])

    con = await asyncpg.connect(get_connection_url())
    await con.execute(qry)
    await con.close()


async def insert_data(
    con: asyncpg.Connection, table_name: str, col_names: list[str], values: list[tuple]
) -> None:
    query_args = f'({', '.join([f'${i}' for i in range(1, len(col_names) + 1)])})'
    col_names = f'({", ".join(col_names)})'
    stmt = f"INSERT INTO {table_name} {col_names} values {query_args} ;"
    with con.query_logger(detailed_logger):
        async with con.transaction():
            await con.executemany(stmt, values)


async def load_todos(con: asyncpg.Connection, size: int = 10) -> None:
    colnames = ["owner", "status"]
    values = [(f"todo{i}", random_choice_enum(TodoStatus)) for i in range(1, size + 1)]
    await insert_data(con, "todos", colnames, values)


async def load_tasks(con: asyncpg.Connection, size: int = 10) -> None:
    colnames = ["brief", "contents", "todo_id", "status", "priority", "category", "due"]
    due = now()
    values = [
        [
            f"brief{i}",
            f"contents{i}",
            1,
            random_choice_enum(TaskStatus),
            random_choice_enum(TaskPriority),
            f"category{i}",
            due,
        ]
        for i in range(1, size + 1)
    ]
    await insert_data(con, "tasks", colnames, values)


async def load_all(todos_size: int=10, tasks_size:int=10):
    con = await asyncpg.connect(get_connection_url())
    await load_todos(con, todos_size)
    await load_tasks(con, tasks_size)
    await con.close()


async def cleanup_table(con: asyncpg.Connection, table_name: str) -> None:
    async with con.transaction():
        await con.execute(f"DELETE FROM {table_name};")

async def cleanup_db()->None:
    con = await asyncpg.connect(get_connection_url())
    async with con.transaction():
        await con.execute("DELETE FROM tasks; DELETE FROM todos;")

async def drop_db():
    conn = await asyncpg.connect(get_connection_url(database="postgres"))

    with conn.query_logger(detailed_logger):
        await conn.execute(f"DROP DATABASE {settings.PG_DB};")
        await conn.close()