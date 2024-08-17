import logging

from quart import Blueprint, ResponseReturnValue, current_app, request
from quart_schema import (
    validate_querystring,
    validate_request,
    validate_response,
)
from werkzeug.exceptions import NotFound

from src.data.repository import TaskRepository as Repository
from src.domain.models import Task, UpdateTask
from src.service.task import TaskService as Service

from .schemas import CreateTaskNoTodoId, ListTasksQueryArgs, TaskList

logger = logging.getLogger(__name__)

bp = Blueprint("tasks", __name__)


@bp.before_request
async def inject_service():
    con = await current_app.db_pool.acquire()
    repo = Repository(con, current_app.db_pool)
    service = Service(repo)
    request.db_con = con
    request.service = service


@bp.after_request
async def release_con(_request):
    await current_app.db_pool.release(request.db_con)
    return _request


@bp.errorhandler(404)
async def todo_not_found(error):
    err_message = "Task not found"
    if (description := getattr(error, "description", None)) is not None:
        err_message = description
    return err_message, 404


@bp.get("/<int:todo_id>/tasks/")
@validate_querystring(ListTasksQueryArgs)
@validate_response(TaskList)
async def list_tasks(todo_id: int, query_args: ListTasksQueryArgs) -> TaskList:
    query_args = query_args.to_service_query_schema()
    # Add `todo_id` to filters to prevent arbitrary task search.
    query_args["filters"].update(todo_id=[todo_id])
    tasks = await request.service.get_many(**query_args)
    return TaskList(tasks=tasks)


@bp.post("/<int:todo_id>/tasks/")
@validate_request(CreateTaskNoTodoId)
@validate_response(Task, 201)
async def add_task(todo_id: int, data: CreateTaskNoTodoId) -> Task:
    task = await request.service.create(
        **data.model_dump(exclude_none=True), todo_id=todo_id
    )
    return task, 201


@bp.get("/<int:todo_id>/tasks/<int:task_id>/")
@validate_response(Task)
async def get_task(todo_id: int, task_id: int) -> Task:
    task = await request.service.get_one(task_id=task_id)

    if not task:
        raise NotFound(
            f"Task with id {task_id} or Todo list with id {todo_id} not found"
        )

    return task


@bp.patch("/<int:todo_id>/tasks/<int:task_id>/")
@validate_request(UpdateTask)
@validate_response(Task)
async def update_task(todo_id: int, task_id: int, data: UpdateTask) -> Task:
    task = await request.service.update(task_id=task_id, payload=data)

    if not task:
        raise NotFound(
            f"Task with id {task_id} or Todo list with id {todo_id} not found"
        )

    return task


@bp.delete("/<int:todo_id>/tasks/<int:task_id>/")
async def delete_task(todo_id: int, task_id: int) -> ResponseReturnValue:
    deleted = await request.service.delete(task_id=task_id)

    if not deleted:
        raise NotFound(
            f"Task with id {task_id} or Todo list with id {todo_id} not found"
        )

    return "", 204
