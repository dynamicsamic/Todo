from pydantic_settings import BaseSettings
from zoneinfo import ZoneInfo


class Settings(BaseSettings):
    TZ: ZoneInfo = ZoneInfo("Europe/Moscow")
    DEFAULT_PAGE_LIMIT: int = 10
    MAX_PAGE_LIMIT: int = 100


settings = Settings()
