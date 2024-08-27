# Todo list

## Basic application for perfomring CRUD operations on todo lists

### Features
* four layers architecture: *data* -> *service* -> *domain* -> *web*
    * `data` layer provides an interface for performing efficient database queries with query results stored in lightweight Row objects (based on namedtuples)
    * `service` layer abstracts the process of database communication, converts database queries to domain models and provides an interface for the web layer
    * `domain` layer describes key application entities (models and types) which service and web layers must conform to, thus ensuring the design by contract principles
    * `web` layer provides convienient client interfaces (for now only the REST API) for interacting with the application 
* database connection pooling with `asyncpg` for the lifespan of the application
* auto-generated `OpenAPI schema` by QuartSchema
* **97% unit and end-to-end test covarage** with `pytest`, `pytest_asyncio` and `unittest.Mock`
* **CLI commands** for applying migrations and loading test data
* `Ruff` linting and `Black` formatting
* dependency management with `PDM`
* CI with `GitHub Actions`

### Built with
* Quart
* Asyncpg
* Pydantic
* Pytest

### Installation
Note: You need to have `docker` installed on your machine.
* create a directory for your project `mkdir todo && cd todo`
* copy `docker-compose.yml` to the project directory
* add `.env` file to the project directory
* run `docker-compose up -d --build` to build and start the application

### Usage

#### CLI commands:
**DATABASE**
`pdm init_db`: initialize the database
`pdm migrate`: apply one migration (read further for details)
`pdm migrate_all`: apply all migrations
`pdm prepare_db`: initialize the database and apply all migrations
`pdm load_test_data`: load test data (mainly for test purposes)
`pdm drop_db`: drop the database (mainly for test purposes)

**MIGRATION OPTIONS**
`pdm migrate <file_name>`: apply one migration
`pdm migrate <file_name> -d`: downgrade one migration
`pdm migrate_all`: apply all migrations
`pdm migrate_all -d`: downgrade all migrations

*Migration mechanism comes with several constraints:*
* migration files are stored in `src/data/migrations`
* every migration have two module-scope variables `upgrade` and `downgrade`

**RUN OPTIONS**
`pdm dev_server`: start the development server
`pdm prod_server`: start the production server
`pdm start_dev_app`: prepare db, load test data and start the development server
`pdm start_app`: prepare db and start the production server

**TESTING**
`pdm lint`: run linters and formatters
`pdm test`: run the tests


### Roadmap
- [ ] Add User model and add reference to it in Todo model
- [ ] Add user-scope restrictions to Todo queries
- [ ] Add registration and login mechanisms
- [ ] Add throttling to API queries
- [ ] Add TaskCategory model instead of plain text

### License
Distributed under the MIT License. See `LICENSE.txt` for more information.