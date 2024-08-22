from pydantic_settings import BaseSettings, SettingsConfigDict
from zoneinfo import ZoneInfo

TEST_PG_USER = "test_user"
TEST_PG_PASS = "test_user"
TEST_PG_DB = "test_todo_list"
TEST_PG_HOST = "localhost"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    DEBUG: bool = True
    TZ: ZoneInfo = ZoneInfo("Europe/Moscow")
    DEFAULT_PAGE_LIMIT: int = 10
    MAX_PAGE_LIMIT: int = 100

    TODO_DB_NAME: str = "todos"
    TASK_DB_NAME: str = "tasks"

    PG_USER: str = TEST_PG_USER
    PG_PASSWORD: str = TEST_PG_PASS
    PG_HOST: str = TEST_PG_HOST
    PG_PORT: int = 5432
    PG_DB: str = TEST_PG_DB


settings = Settings()
