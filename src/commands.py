import asyncio
import logging

import click
from quart import Quart

from src.data import db
from src.settings import settings

logger = logging.getLogger(__name__)


def app_cli(app: Quart) -> Quart:
    @click.option("-f", "--file")
    @click.option("-a", "--apply_all", is_flag=True, default=False)
    @click.option("-d", "--downgrade", is_flag=True, default=False)
    @app.cli.command("migrate")
    def migrate(file: str, apply_all: bool, downgrade: bool):
        migration_type = "downgrade" if downgrade else "upgrade"
        target = file if file else "all"
        print(f"Applying `{migration_type}` migrations to {target}.")

        try:
            asyncio.get_event_loop().run_until_complete(
                db.apply_migration(file, migration_type)
            )
        except Exception as err:
            print(f"Migrations failed with error: {err}")
            return

        print(f"`{migration_type}` migrations applied to {target}.")

    @app.cli.command("init_db")
    def init_db():
        print(f"Initializing database {settings.PG_DB}.")
        asyncio.get_event_loop().run_until_complete(db.check_db_created())
        print(f"Database {settings.PG_DB} initialized successfully.")

    @app.cli.command("load_data")
    def load_data():
        print("Loading test data.")
        asyncio.get_event_loop().run_until_complete(db.load_all())
        print("Test data loaded successfully.")

    @app.cli.command("create_test_app")
    def create_test_app():
        print("Creating test app...")
        print("Checking if database exists...")
        asyncio.get_event_loop().run_until_complete(db.check_db_created())
        print("Applying migrations...")
        asyncio.get_event_loop().run_until_complete(db.apply_migration())
        print("Loading test data...")
        asyncio.get_event_loop().run_until_complete(db.load_all())
        print("Test app created successfully.")

    return app
