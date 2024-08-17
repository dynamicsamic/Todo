import functools
import logging
from typing import Any, Awaitable, Callable, Type

from pydantic import ValidationError

from src.domain.models import BaseModel

logger = logging.getLogger(__name__)


class BadResponse(Exception):
    pass


class BadRequest(Exception):
    pass


def validate_input_output(
    *,
    input_model: Type[BaseModel],
    output_model: Type[BaseModel],
    return_list: bool = False,
) -> Callable[[Awaitable], (Awaitable)]:
    """
    Provide complete validation for a service method.

    Validates input data against input model. Runs the decorated function
    with validated arguments. Finally validates the resulting data against 
    the output model.

    Default arguments of the decorated function will be lost during the 
    execution process. Provide sane default values for the input model.

    Args:
        input_model: A pydantic model that validates the input data.
        output_model: A pydantic model that validates the output data.
        return_list: Flag to convert the result to a list of models.
    
    >>> class SomeService:
    ...     @validate_input_output(input_model=InputModel, output_model=OutputModel)
    ...     async def some_method(self, *args, **kwargs) -> OutputModel:
    ...         ...
    """

    def decorator(func: Awaitable) -> Awaitable:
        @functools.wraps(func)
        async def wrapper(
            *args: Any, **kwargs: Any
        ) -> BaseModel | list[BaseModel] | None:
            if len(args) > 1:
                raise TypeError(
                    f"Function {func} takes 0 positional "
                    f"arguments but {len(args) - 1} were given"
                )

            try:
                valid_data = input_model.model_validate(kwargs)
            except ValidationError as err:
                logger.error(
                    f"Parsing query arguments from client failed with error: {err}."
                    f"Invalid query arguments received: {kwargs}"
                )
                raise BadRequest from err

            result = await func(
                *args, **valid_data.model_dump(exclude_none=True)
            )

            if result is None:
                return None

            try:
                validated = (
                    output_model.model_validate(result)
                    if not return_list
                    else [output_model.model_validate(item) for item in result]
                )
            except ValidationError as err:
                logger.error(
                    f"Parsing db response failed with error: {err}. "
                    f"Invalid model received: {result}"
                )
                raise BadResponse from err

            return validated

        return wrapper

    return decorator


def validate_query(model_type: Type[BaseModel]):
    def decorator(func: Awaitable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if len(args) > 1:
                raise TypeError(
                    f"Function {func} takes 0 positional "
                    f"arguments but {len(args) - 1} were given"
                )
            try:
                valid_data = model_type.model_validate(kwargs)
            except ValidationError as err:
                logger.error(
                    f"Parsing query arguments from client failed with error: {err}."
                    f"Invalid query arguments received: {kwargs}"
                )
                raise BadRequest from err

            return await func(
                *args, **valid_data.model_dump(exclude_none=True)
            )

        return wrapper

    return decorator


def validate_response(
    model_type: Type[BaseModel], many: bool = False
) -> Callable[[Awaitable], (Awaitable)]:
    def decorator(func: Awaitable) -> Awaitable:
        @functools.wraps(func)
        async def wrapper(
            *args, **kwargs
        ) -> BaseModel | list[BaseModel] | None:
            if len(args) > 1:
                raise TypeError(
                    f"Function {func.__code__.co_name} takes 0 positional "
                    f"arguments but {len(args) - 1} were given"
                )
            result = await func(*args, **kwargs)
            if result is None:
                return None
            try:
                validated = (
                    model_type.model_validate(result)
                    if not many
                    else [model_type.model_validate(item) for item in result]
                )
            except ValidationError as err:
                logger.error(
                    f"Parsing db response failed with error: {err}. "
                    f"Invalid model received: {result}"
                )
                raise BadResponse from err

            return validated

        return wrapper

    return decorator
