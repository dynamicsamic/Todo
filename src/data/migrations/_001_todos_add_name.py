from src.settings import settings

colname = "name"


upgrade = f"""
ALTER TABLE {settings.TODO_DB_NAME}
ADD COLUMN {colname} varchar(60) NOT NULL DEFAULT 'Universal Todo';
ALTER TABLE {settings.TODO_DB_NAME} ALTER COLUMN name DROP DEFAULT;
"""

downgrade = f"""
ALTER TABLE {settings.TODO_DB_NAME}
DROP COLUMN {colname};
"""
