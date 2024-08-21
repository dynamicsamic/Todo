from src.settings import settings

upgrade = f"""
    DO $$ BEGIN
        CREATE TYPE todo_status AS ENUM ('active', 'inactive');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;


    DO $$ BEGIN
        CREATE TYPE task_status AS ENUM ('pending', 'complete', 'postponed');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;


    DO $$ BEGIN
        CREATE TYPE task_priority AS ENUM ('low', 'medium', 'high');
    EXCEPTION
        WHEN duplicate_object THEN null;
    END $$;

    
    CREATE TABLE IF NOT EXISTS todos 
        (
            todo_id serial PRIMARY KEY, 
            owner varchar(120) UNIQUE NOT NULL, 
            status todo_status NOT NULL,
            created_at timestamptz NOT NULL DEFAULT NOW(), 
            updated_at timestamptz NOT NULL DEFAULT NOW()
        );


    CREATE TABLE IF NOT EXISTS tasks 
        (
            task_id serial PRIMARY KEY,
            brief varchar(300) NOT NULL,
            todo_id int NOT NULL REFERENCES todos(todo_id) ON DELETE CASCADE,
            contents text,
            status task_status NOT NULL DEFAULT 'pending',
            priority task_priority NOT NULL DEFAULT 'low',
            category varchar(100) NOT NULL,
            due timestamptz NOT NULL,
            created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP, 
            updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
        
        );


    ALTER DATABASE {settings.PG_DB} SET timezone TO 'Europe/Moscow';
"""


downgrade = """ 
    DROP TABLE IF EXISTS tasks; 
    DROP TABLE IF EXISTS todos; 
    DROP TYPE todo_status; 
    DROP TYPE task_status; 
    DROP TYPE task_priority; 
"""
