import logging

import asyncpg

from src.domain.types import TaskPriority, TaskStatus, TodoStatus
from src.utils import AsyncpgQueryLogger, now, random_choice_enum

logger = logging.getLogger(__name__)

simple_logger = AsyncpgQueryLogger(logger, detailed=False)
detailed_logger = AsyncpgQueryLogger(logger)


create_todo_status_qry = """
    DO $$ BEGIN
        CREATE TYPE todo_status AS ENUM ('active', 'inactive');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
"""

create_task_status_qry = """
    DO $$ BEGIN
        CREATE TYPE task_status AS ENUM ('pending', 'complete', 'postponed');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
"""

create_task_priority_qry = """
    DO $$ BEGIN
        CREATE TYPE task_priority AS ENUM ('low', 'medium', 'high');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;
"""


create_tasks_table_qry = """
    DROP TABLE IF EXISTS tasks;
    CREATE TABLE tasks 
        (
            task_id serial PRIMARY KEY,
            brief varchar(300) NOT NULL,
            todo_id int NOT NULL REFERENCES todos(todo_id) ON DELETE CASCADE,
            contents text,
            status task_status NOT NULL DEFAULT 'pending',
            priority task_priority NOT NULL DEFAULT 'low',
            category varchar(100) NOT NULL,
            due timestamptz NOT NULL,
            created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP, 
            updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
        
        )
"""

create_todos_table_qry = """
    DROP TABLE IF EXISTS todos CASCADE;
    CREATE TABLE todos 
        (
            todo_id serial PRIMARY KEY, 
            owner varchar(120) UNIQUE NOT NULL, 
            status todo_status NOT NULL,
            created_at timestamptz NOT NULL DEFAULT NOW(), 
            updated_at timestamptz NOT NULL DEFAULT NOW()
        );
"""


async def init_db(
    user: str,
    password: str,
    database: str,
    host: str = "localhost",
    port: int = 5432,
) -> None:
    try:
        conn = await asyncpg.connect(
            user=user,
            password=password,
            database=database,
            host=host,
            port=port,
        )
    except asyncpg.InvalidCatalogNameError:
        conn = await asyncpg.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database="template1",
        )
        await conn.execute(f"CREATE DATABASE {database};")

    with conn.query_logger(simple_logger):
        await conn.execute(
            f"ALTER DATABASE {database} SET timezone TO 'Europe/Moscow';"
        )
        await conn.execute(create_todo_status_qry)
        await conn.execute(create_task_status_qry)
        await conn.execute(create_task_priority_qry)
        await conn.execute(create_todos_table_qry)
        await conn.execute(create_tasks_table_qry)
        await conn.close()


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


async def cleanup_table(con: asyncpg.Connection, table_name: str) -> None:
    async with con.transaction():
        await con.execute(f"DELETE FROM {table_name};")
