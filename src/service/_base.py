import logging
from typing import Any

from src.data.repository import Repository
from src.domain.models import BaseModel
from src.settings import settings

logger = logging.getLogger(__name__)


class Service:
    """Base class for all services.
    The main purpose of a service is to provide a common interface
    between the data layer and consuming layers like the API.

    In combination with validators from `.validation` module,
    it is capable of:

    - validating incoming data for making database requests;
    - performing basic CRUD operations;
    - validating and serializing database responses to domain models.
    """

    def __init__(self, repository: Repository) -> None:
        self.repo = repository

    async def get_one(self, *, pk: Any, **kwargs: Any) -> BaseModel | None:
        return await self.repo.fetch_one(pk, **kwargs)

    async def get_many(
        self,
        *,
        limit: int = settings.DEFAULT_PAGE_LIMIT,
        offset: int = 0,
        filters: dict[str, list[Any]] | None = None,
        **kwargs: Any,
    ) -> list[BaseModel]:
        return await self.repo.fetch_many(
            limit=limit, offset=offset, filters=filters, **kwargs
        )

    async def create(self, **payload: Any) -> BaseModel | None:
        try:
            return await self.repo.insert_one(**payload)
        except Exception as err:
            logger.error(
                f"Eror during instance creation. Data: {payload}. Error: {err}"
            )
            raise

    async def update(
        self, *, pk: Any, payload: BaseModel, **kwargs: Any
    ) -> BaseModel | None:
        try:
            return await self.repo.update_one(pk, payload)
        except Exception as err:
            logger.error(
                "Error during instance update. "
                f"pk: {pk}. Data: {payload}. Error: {err}"
            )
            raise

    async def delete(self, *, pk: Any) -> bool:
        try:
            deleted = await self.repo.delete_one(pk)
        except Exception as err:
            logger.error(f"Error during instance delete. PK: {pk}. Error: {err}")
            raise

        return bool(deleted)
