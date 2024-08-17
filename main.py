import logging

import asyncpg
from quart import Quart
from quart_schema import QuartSchema, ResponseSchemaValidationError

from src.data.db import init_db
from src.utils import AsyncpgQueryLogger
from src.web.api import bp

app = Quart(__name__)
app.debug = True
QuartSchema(app, convert_casing=True, conversion_preference="pydantic")
app.register_blueprint(bp, url_prefix="/todos")

logger = logging.getLogger(__name__)
query_logger = AsyncpgQueryLogger(logger)


TEST_PG_USER = "test_user"
TEST_PG_PASS = "test_user"
TEST_PG_DB_NAME = "test_todo_list"
@app.before_serving
async def create_db():
    await init_db(TEST_PG_USER, TEST_PG_PASS, TEST_PG_DB_NAME)


@app.before_serving
async def create_db_pool():
    logger.info("Starting DB Connection Pool")
    app.db_pool = await asyncpg.create_pool(
        f"postgresql://{TEST_PG_USER}:{TEST_PG_PASS}@localhost:5432/{TEST_PG_DB_NAME}"
    )
    
# @app.while_serving
# async def lifespan():
#     # async with app.db_pool.acquire() as con:
#         # g.db_session = con
#     print(dir(g))
#         # request["db_session"] = con
#         # print(request.db_session)
#     yield
    ...  # shutdown
@app.after_serving
async def close_db_pool():
    logger.info("Closing DB Connection Pool")
    await app.db_pool.close()
    conn = await asyncpg.connect(
            user=TEST_PG_USER,
            password=TEST_PG_PASS,
            database='template1',
            host="localhost",
            port=5432,
        )
    
    with conn.query_logger(query_logger):
        await conn.execute(f'DROP DATABASE {TEST_PG_DB_NAME};')
        await conn.close()

@app.errorhandler(ResponseSchemaValidationError)
async def handle_response_validation_error():
    return {"error": "VALIDATION"}, 500


@app.route("/")
async def hello():
    return "hello"


# if __name__ == "__main__":
    # app.run(debug=True)
