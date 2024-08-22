import pytest
from pytest_asyncio import is_async_test

from src.settings import settings

TODO_SAMPLE_SIZE = 1000
TASK_SAMPLE_SIZE = 1500
DEFAULT_LIMIT = settings.DEFAULT_PAGE_LIMIT


def pytest_collection_modifyitems(items):
    """
    Make all fixtures and tests run in module scope.
    Prevents asyncpg InterfaceError <class 'asyncpg.exceptions._base.InterfaceError'>:
    cannot perform operation: another operation is in progress.
    This happens because of pytest_asyncio runs creates differnt ivent loops for
    each single test. Meanwhile all connections from asyncpg's connection pool
    should run in a single event loop.
    """
    pytest_asyncio_tests = (item for item in items if is_async_test(item))
    module_scope_marker = pytest.mark.asyncio(scope="module")
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(module_scope_marker, append=False)
