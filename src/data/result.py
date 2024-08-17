from collections import namedtuple
from typing import TypeVar

DataRow = TypeVar("DataRow", bound=namedtuple)


TodoRow = namedtuple(
    "Todo",
    ["todo_id", "owner", "status", "created_at", "updated_at", "tasks"],
)
TodoRow.__doc__ = "Data that represents one row in `todos` table"
TaskRow = namedtuple(
    "Task",
    [
        "task_id",
        "brief",
        "todo_id",
        "contents",
        "status",
        "priority",
        "category",
        "due",
        "created_at",
        "updated_at",
    ],
)
TaskRow.__doc__ = "Data that represents one row in `tasks` table"
