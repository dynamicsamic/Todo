from quart import Blueprint

from .task import bp as task_bp
from .todo import bp as todo_bp

bp = Blueprint("todos", __name__)

bp.register_blueprint(todo_bp, name="todo")
bp.register_blueprint(task_bp, name="task")
