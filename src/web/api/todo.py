import logging

from pydantic import ValidationError
from quart import Blueprint, ResponseReturnValue, current_app, request
from quart_schema import (
    validate_querystring,
    validate_request,
    validate_response,
)
from werkzeug.exceptions import NotFound

from src.data.repository import TodoRepository as Repository
from src.domain.models import CreateTodo, Todo, UpdateTodo
from src.service.todo import TodoService as Service

from .schemas import (
    GetTodoQueryArgs,
    ListTodosQueryArgs,
    TodoList,
)

logger = logging.getLogger(__name__)

bp = Blueprint("todos", __name__)


@bp.before_request
async def inject_service():
    con = await current_app.db_pool.acquire()
    repo = Repository(con, current_app.db_pool)
    service = Service(repo)
    request.db_con = con
    request.service = service


@bp.after_request
async def release_con(_request):
    try:
        await current_app.db_pool.release(request.db_con)
    except Exception as err:
        logger.error(f"Error during db release. Error: {err}.")
        pass
    return _request


@bp.errorhandler(404)
async def todo_not_found(error):
    err_message = "Todo not found"
    if (description := getattr(error, "description", None)) is not None:
        err_message = description
    return err_message, 404


def with_validation_error(value):
    try:
        return value
    except ValidationError as err:
        logger.error(
            f"invalid response from service. Reponse: {value}. Error: {err}"
        )
        raise


@bp.get("/")
@validate_querystring(ListTodosQueryArgs)
@validate_response(TodoList)
async def list_todos(query_args: ListTodosQueryArgs) -> TodoList:
    query_args = query_args.to_service_query_schema()
    todos = await request.service.get_many(**query_args)
    return TodoList(todos=todos)


@bp.post("/")
@validate_request(CreateTodo)
@validate_response(Todo, 201)
async def add_todo(data: CreateTodo) -> Todo:
    todo = await request.service.create(**data.model_dump())
    return todo, 201


@bp.get("/<int:todo_id>/")
@validate_querystring(GetTodoQueryArgs)
async def get_todo(todo_id: int, query_args: GetTodoQueryArgs) -> Todo:
    prefetch = query_args.prefetch_tasks
    todo = await request.service.get_one(
        todo_id=todo_id, prefetch_tasks=prefetch
    )

    if not todo:
        raise NotFound(f"Todo with id {todo_id} not found")

    return todo


@bp.patch("/<int:todo_id>/")
@validate_request(UpdateTodo)
@validate_response(Todo)
async def update_todo(todo_id: int, data: UpdateTodo) -> Todo:
    todo = await request.service.update(todo_id=todo_id, payload=data)

    if not todo:
        raise NotFound(f"Todo with id {todo_id} not found")

    return todo


@bp.delete("/<int:todo_id>/")
async def delete_todo(todo_id: int) -> ResponseReturnValue:
    deleted = await request.service.delete(todo_id=todo_id)
    if not deleted:
        raise NotFound(f"Todo with id {todo_id} not found")

    return "", 204
