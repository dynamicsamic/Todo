import logging

import asyncpg
from quart import Quart
from quart_schema import QuartSchema, ResponseSchemaValidationError

from src.data.db import init_db
from src.settings import settings
from src.utils import AsyncpgQueryLogger
from src.web.api import bp

app = Quart(__name__)
app.debug = settings.DEBUG
QuartSchema(app, convert_casing=True, conversion_preference="pydantic")
app.register_blueprint(bp, url_prefix="/todos")

logger = logging.getLogger(__name__)
query_logger = AsyncpgQueryLogger(logger)


@app.before_serving
async def create_db():
    await init_db(settings.PG_USER, settings.PG_PASSWORD, settings.PG_DB)


@app.before_serving
async def create_db_pool():
    logger.info("Starting DB Connection Pool")
    dsn = (
        f"postgresql://{settings.PG_USER}:{settings.PG_PASSWORD}"
        f"@{settings.PG_HOST}:{settings.PG_PORT}/{settings.PG_DB}"
    )
    app.db_pool = await asyncpg.create_pool(
        dsn, min_size=1, max_size=50, command_timeout=10
    )


@app.after_serving
async def close_db_pool():
    logger.info("Closing DB Connection Pool")
    await app.db_pool.close()


@app.after_serving
async def cleanup_db():
    conn = await asyncpg.connect(
        user=settings.PG_USER,
        password=settings.PG_PASSWORD,
        database="template1",
        host=settings.PG_HOST,
        port=settings.PG_PORT,
    )

    with conn.query_logger(query_logger):
        await conn.execute(f"DROP DATABASE {settings.PG_DB};")
        await conn.close()


@app.errorhandler(ResponseSchemaValidationError)
async def handle_response_validation_error():
    return {"error": "VALIDATION"}, 500


@app.route("/")
async def health_check():
    return {"healthy": True}
