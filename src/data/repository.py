import logging
from datetime import datetime
from itertools import chain
from types import TracebackType
from typing import Any, Generator, Iterable, Type

from asyncpg import Connection, InterfaceError, Record
from asyncpg.pool import Pool

from src.domain.types import TaskPriority, TaskStatus, TodoStatus
from src.settings import settings
from src.utils import AsyncpgQueryLogger

from .result import DataRow, TaskRow, TodoRow
from .sql import (
    estimated_count,
    generate_delete,
    generate_insert,
    generate_select,
    generate_update,
    prefetch_tasks_query,
    select_order_limit,
)

DEFAULT_LIMIT = settings.DEFAULT_PAGE_LIMIT


logger = logging.getLogger(__name__)

query_logger = AsyncpgQueryLogger(logger)


class ConnectionManager:
    """
    Provides an asyncpg connection to the repository.

    The connection should be passed to Connection Manager using 
    `asyncpg.Pool.acquire()` without `async with` context. 
    Using `async with` will release the connection prematurely.

    After the context manager exits, it will realase the connection back to
    the pool, firstly attempting to close the connection.

    >>> async with ConnectionManager(con, pool) as con:
    ...     await con.execute(...)
    or
    >>> self.connection = ConnectionManager(con, pool)
    >>> async with self.connection as con:
    ...     await con.execute(...)
    """

    def __init__(self, con: Connection, pool: Pool):
        self.con = con
        self.pool = pool

    async def __aenter__(self) -> Connection:
        self.con.add_query_logger(query_logger)
        return self.con

    async def __aexit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        try:
            # The connection may have already been realeased to the pool
            # when the context manager exits.
            self.con.remove_query_logger(query_logger)
            await self.con.close()
        except InterfaceError:
            pass
        finally:
            await self.pool.release(self.con)


class Repository:
    """
    Base class for all repositories.

    Provides a generic interface for basic database operations.

    Class arguments that Repository subclasses must provide:
        `table: str` SQL table name
        `pk: str` Primary key column name
        `row: DataRow` Virtually any data type capable of storing data 
            from `asyncpg.Record`. Represents one table row.

    >>> class UserRepository(Repository):
    ...     table = "users"
    ...     pk = "user_id"
    ...     row = UserRow
    """

    table: str
    pk: str
    row: DataRow
    LIMIT: int = DEFAULT_LIMIT
    pg_type_casts = {
        "todos": {
            "owner": "",
            "todo_id": "::int",
            "status": "::todo_status",
            "created_at": "::timestamp",
            "udpated_at": "::timestamp",
        },
        "tasks": {
            "brief": "",
            "contents": "",
            "category": "",
            "task_id": "::int",
            "todo_id": "::int",
            "status": "::task_status",
            "priority": "::task_priority",
            "due": "::timestamp",
            "created_at": "::timestamp",
            "udpated_at": "::timestamp",
        },
    }

    def __init__(self, connection: Connection, con_pool: Pool) -> None:
        self.connection = ConnectionManager(connection, con_pool)
        self.type_cast = self.pg_type_casts[self.table]

    async def fetch_one(self, pk: Any, *args, **kwargs) -> DataRow | None:
        """Fetch one record from the database based on a primary key."""
        async with self.connection as con:
            async with con.transaction():
                res = await con.fetchrow(
                    generate_select(self.table, self.pk), pk
                )

        return self._create_row(res) if res else None

    async def fetch_many(
        self,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        order_by: list[str] = None,
        filters: dict[str, list[str]] | None = None,
    ) -> Generator[DataRow, None, None]:
        """Fetch multiple records from the database based on provided arguments.
        
        >>> request = await repository.fetch_many(
        ... limit=2, offset=10, order_by=["created_at"],
        ... filters={"status": ["completed", "deleted"]}
        ... )
        >>> result = list(request)
        """
        res = await self._fetch(
            select_order_by=order_by,
            limit=limit,
            offset=offset,
            filters=filters,
        )
        return (self._create_row(item) for item in res)

    async def insert_one(
        self, **create_data: dict[str, Any]
    ) -> DataRow | None:
        """Insert a new row into the database.
        >>> new_obj = await repository.insert_one(
        ...     owner="johndoe", status='active'
        ... )
        """
        cols = list(create_data)
        vals = list(create_data.values())
        qry = generate_insert(self.table, cols, [vals])
        async with self.connection as con:
            async with con.transaction():
                res = await con.fetchrow(qry, *vals)

        return self._create_row(res) if res else None

    async def update_one(
        self, pk: Any, update_data: dict[str, Any]
    ) -> DataRow | None:
        """Update a record in the database based on a primary key.

        >>> updated_obj = await repository.update_one(
        ...     pk=1, update_data={owner:"johndoe", status:'active'}
        ... )
        """
        qry = generate_update(self.table, self.pk, update_data)
        async with self.connection as con:
            async with con.transaction():
                res = await con.fetchrow(qry, pk, *update_data.values())

        return self._create_row(res) if res else None

    async def delete_one(self, pk: Any) -> int | None:
        """Delete a record in the database based on a primary key.

        >>> deleted_id = await repository.delete_one(pk=1)
        """
        qry = generate_delete(self.table, self.pk)
        async with self.connection as con:
            async with con.transaction():
                return await con.fetchval(qry, pk)

    async def estimate(self) -> int:
        """Estimate the number of records in the database.
        A more efficient way to get the number of records in a table.

        >>> count = await repository.estimate()
        """
        qry = estimated_count.format(table_name=self.table)
        async with self.connection as con:
            async with con.transaction():
                count = await con.fetchval(qry)
                if count < 0:
                    await con.execute(f"ANALYZE {self.table};")
                    count = await con.fetchval(qry)
        return count

    async def _fetch(
        self,
        select_columns: list[str] = None,
        select_order_by: list[str] = None,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        filters: dict[str, list[Any]] | None = None,
    ) -> list[Record]:
        """Constructs a select query with `WHERE`, `ORDER BY` and `LIMIT` instructions
        and fetches the results from the database.
        Used as a basis for `fetch many` queries.
        """
        if not select_order_by:
            select_order_by = [self.pk]

        order_by = ", ".join(select_order_by)
        columns = "*" if not select_columns else ", ".join(select_columns)
        where_clause = ""
        args = []

        # Set the offset. More efficient than default sql `OFFSET` instruction.
        where_clause = f"WHERE {self.pk} > $2"

        if filters:
            query_args = self._prepare_query_args(filters, 3)
            where_clause = f"{where_clause} AND {query_args}"
            filter_values = filters.values()
            args = chain.from_iterable(filter_values)

        qry = select_order_limit.format(
            columns=columns,
            table_name=self.table,
            where_clause=where_clause,
            order_by=order_by,
        )
        async with self.connection as con:
            async with con.transaction():
                return await con.fetch(qry, limit, offset, *args)

    def _prepare_query_args(
        self, query_args: dict[str, list[Any]], i: int = 1
    ) -> str:
        """Generates a 'selection from multiple values' statements joined with `AND`.
        Columns types different from varchar are casted to their corresponding types using
        self.type_cast table.
        Generally this is more efficient than using `IN` statements.

        >>> query_args = {
        ...     "owner": ["johndoe", "janedoe"],
        ...     "status": ["active", "inactive"],
        ...     "priority": [TaskPriority.high, TaskPriority.low],
        ... }
        >>> self._prepare_query_args(query_args)
        >>> 'owner = any (values $1, $2) AND status = any (values $3, $4) AND priority = any (values $5, $6)'
        """
        parts = []

        for col_name, vals in query_args.items():
            col_type = self.type_cast[col_name]
            subs = ", ".join(
                f"(${j}{col_type})" for j in range(i, len(vals) + i)
            )
            part = f"{col_name} = any (values {subs})"
            parts.append(part)
            i += len(vals)

        return " AND ".join(parts)

    def _create_row(self, record: Record, **kwargs: Any) -> DataRow:
        return self.row(**record, **kwargs)


class TodoRepository(Repository):
    table = "todos"
    pk = "todo_id"
    row = TodoRow

    async def fetch_many(
        self,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        order_by: list[str] = None,
        filters: dict[str, list[str]] | None = None,
    ) -> Generator[TodoRow, None, None]:
        return await super().fetch_many(limit, offset, order_by, filters)

    async def fetch_one(
        self, todo_id: int, prefetch_tasks: int = 0
    ) -> TodoRow | None:
        """Fetch a single record from todos table.
        If `prefetch_tasks > 0`, additional database query will be executed
        to fetch related tasks. Tasks then converted to a generator of TaskRow.
        """
        tasks = None
        qry = generate_select(self.table, self.pk)
        async with self.connection as con:
            async with con.transaction():
                todo = await con.fetchrow(qry, todo_id)
            if not todo:
                return None

            if prefetch_tasks:
                tasks = await con.fetch(
                    prefetch_tasks_query, todo_id, prefetch_tasks
                )

        if tasks:
            tasks = (TaskRow(**task) for task in tasks)

        return self._create_row(todo, tasks=tasks)

    async def insert_one(
        self,
        *,
        owner: str,
        status: TodoStatus = TodoStatus.ACTIVE,
    ) -> TodoRow | None:
        return await super().insert_one(owner=owner, status=status)

    async def update_one(
        self, todo_id: int, update_data: dict[str, Any]
    ) -> TodoRow | None:
        return await super().update_one(todo_id, update_data)

    async def delete_one(self, todo_id: int) -> int | None:
        return await super().delete_one(todo_id)

    def _create_row(
        self, record: Record, tasks: Iterable[TaskRow] | None = None
    ) -> DataRow:
        return self.row(**record, tasks=tasks)


class TaskRepository(Repository):
    table = "tasks"
    pk = "task_id"
    row = TaskRow

    async def fetch_many(
        self,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
        order_by: list[str] = None,
        filters: dict[str, list[str]] | None = None,
    ) -> Generator[TaskRow, None, None]:
        return await super().fetch_many(limit, offset, order_by, filters)

    async def fetch_one(self, task_id: int) -> TaskRow | None:
        return await super().fetch_one(task_id)

    async def insert_one(
        self,
        *,
        brief: str,
        todo_id: int,
        category: str,
        due: datetime,
        contents: str = None,
        status: TaskStatus = TaskStatus.PENDING,
        priority: TaskPriority = TaskPriority.LOW,
    ) -> TaskRow | None:
        return await super().insert_one(
            brief=brief,
            todo_id=todo_id,
            category=category,
            due=due,
            contents=contents,
            status=status,
            priority=priority,
        )

    async def update_one(
        self, task_id: int, update_data: dict[str, Any]
    ) -> TaskRow | None:
        return await super().update_one(task_id, update_data)

    async def delete_one(self, task_id: int) -> int | None:
        return await super().delete_one(task_id)
