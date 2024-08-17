import logging
import random
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable

from asyncpg.connection import LoggedQuery

from src.settings import settings


def datetime_with_delta(delta: dict[str, int]) -> Callable[[], datetime]:
    """
    A factory for creating convinient zero-argument functions that return
    a datetime (based on current datetime) with the specified delta applied.

    The delta is applied using the `datetime.timedelta` function
    which takes keyword arguments for days, seconds, microseconds,
    milliseconds, minutes, hours, and weeks.
    """

    def _inner() -> datetime:
        return datetime.now(tz=settings.TZ) + timedelta(**delta)

    return _inner


now = datetime_with_delta({"microseconds": 0})


class AsyncpgQueryLogger:
    """
    Logs an asyncpg query to the specified logger.

    Should be attached to asyncpg connection either via
    `connection.add_query_logger` function or via
    `with connection.query_logger` context manager.

    The `detailed` parameter logs the SQL query, its arguments and
    elapsed execution time.
    """

    def __init__(self, logger: logging.Logger, detailed: bool = True) -> None:
        self.logger = logger
        self.detailed = detailed

    def __call__(self, rec: LoggedQuery) -> None:
        if self.detailed:
            qry = " ".join(rec.query.split())
            message = f"{qry} args {rec.args}: {rec.elapsed:.5f} sec"
        else:
            message = rec.query

        self.logger.info(message)


def random_choice_enum(enum_type: Enum) -> Any:
    """Choose a random value from an enum."""
    return random.choice(list(enum_type))
