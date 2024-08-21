import logging

import asyncpg
from quart import Quart
from quart_schema import QuartSchema, ResponseSchemaValidationError

from src.commands import app_cli
from src.data.db import get_connection_url
from src.settings import settings
from src.utils import AsyncpgQueryLogger
from src.web.api import bp as api_bp

logger = logging.getLogger(__name__)
query_logger = AsyncpgQueryLogger(logger)


async def create_db_pool():
    logger.info("Starting DB Connection Pool")
    app.db_pool = await asyncpg.create_pool(
        dsn=get_connection_url(), min_size=1, max_size=50, command_timeout=10
    )


async def close_db_pool():
    logger.info("Closing DB Connection Pool")
    await app.db_pool.close()


def create_app():
    app = Quart(__name__)
    app = app_cli(app)
    app.debug = settings.DEBUG
    QuartSchema(app, convert_casing=True, conversion_preference="pydantic")
    app.register_blueprint(api_bp, url_prefix="/api/v1/todos")
    app.before_serving(create_db_pool)
    app.after_serving(close_db_pool)
    return app


app = create_app()


@app.errorhandler(ResponseSchemaValidationError)
async def handle_response_validation_error():
    return {"error": "VALIDATION"}, 500


@app.route("/health", methods=["GET"])
async def health_check():
    return {"healthy": True}
