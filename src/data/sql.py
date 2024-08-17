from typing import Any

basic_select = """
    SELECT {columns}
    FROM {table_name}
    WHERE {column} = $1
"""

select_order_limit_offset = """
    SELECT {columns}
    FROM {table_name}
    {where_clause}
    ORDER BY {order_by}
    LIMIT $1
    OFFSET $2
"""

select_order_limit = """
    SELECT {columns}
    FROM {table_name}
    {where_clause}
    ORDER BY {order_by}
    LIMIT $1
"""

prefetch_tasks_query = """
    SELECT *
    FROM tasks
    WHERE todo_id = $1
    ORDER BY task_id
    LIMIT $2
"""

insert_values = """
    INSERT INTO {table_name}
    ({columns})
    VALUES {values}
    RETURNING *
"""

update_table = """
    UPDATE {table_name}
    SET {columns}
    WHERE {column} = $1
    RETURNING *
"""

delete_from_table = """
    DELETE
    FROM {table_name}
    WHERE {column} = $1
    RETURNING {column}
"""

estimated_count = """
    SELECT  reltuples::bigint AS estimate
    FROM    pg_class
    WHERE   oid = 'public.{table_name}'::regclass;
    """

def generate_select(
    table_name: str, where_column: str, columns: list[str] = None
) -> str:
    columns = "*" if not columns else ", ".join(columns)
    return basic_select.format(
        columns=columns, table_name=table_name, column=where_column
    )


def generate_insert(
    table_name: str, col_names: list[str], values: list[list[Any]]
) -> str:
    parts = []
    i = 1
    columns = ", ".join(col_names)
    for value in values:
        part = f"({', '.join(f"${j}" for j in range(i, len(value) + i))})"
        parts.append(part)
        i += len(value)

    vals = ", ".join(parts)
    return insert_values.format(table_name=table_name, columns=columns, values=vals)


def generate_update(
    table_name: str, where_column: str, update_data: dict[str, Any]
) -> str:
    columns = [f"{key} = ${i}" for i, key in enumerate(update_data.keys(), 2)]
    columns = ", ".join(columns)
    return update_table.format(
        table_name=table_name, columns=columns, column=where_column
    )


def generate_delete(table_name: str, where_column: str) -> str:
    return delete_from_table.format(table_name=table_name, column=where_column)
