import pytest
from pytest_asyncio import is_async_test

# Make all fixtures and tests run in session mode.
# Prevents asyncpg InterfaceError <class 'asyncpg.exceptions._base.InterfaceError'>:
# cannot perform operation: another operation is in progress.
# This happens because of pytest_asyncio runs creates differnt ivent loops for
# each single test. Meanwhile all connections from asyncpg's connection pool
# should run in a single event loop.
# def pytest_collection_modifyitems(items):
#     pytest_asyncio_tests = (item for item in items if is_async_test(item))
#     session_scope_marker = pytest.mark.asyncio(scope="session")
#     for async_test in pytest_asyncio_tests:
#         async_test.add_marker(session_scope_marker, append=False)


def pytest_collection_modifyitems(items):
    pytest_asyncio_tests = (item for item in items if is_async_test(item))
    session_scope_marker = pytest.mark.asyncio(scope="module")
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(session_scope_marker, append=False)
