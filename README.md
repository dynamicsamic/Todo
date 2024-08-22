# Todo list

## Basic application for perfomring CRUD operations on todo lists

### Features:
* four layers architecture: data -> service -> domain -> web
    * data layer provides an interface for performing efficient database queries with query results stored in lightweight Row objects (based on namedtuples)
    * service layer abstracts the process of database communication, converts database queries to domain models and provides an interface for the web layer
    * domain layer describes key application entities (models and types) which service and web layers must conform to, thus ensuring the design by contract principles
    * web layer provides convienient client interfaces (for now only the REST API) for interacting with the application 
* database connection pooling with asyncpg for the lifespan of the application
* auto-generated OpenAPI schema by QuartSchema
* 97% unit and end-to-end test covarage with pytest, pytest_asyncio and unittest.Mock
* CLI commands for applying migrations and loading test data
* Ruff linting and Black formatting
* dependency management with PDM
* CI with GitHub Actions

### Technologies:
* Quart
* Asyncpg
* Pydantic
* Pytest
