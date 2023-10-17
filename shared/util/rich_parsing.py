from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

# Define generic type for `parse_with_error_handling`
T = TypeVar("T", bound=BaseModel)


def parse_with_error_handling(model: Type[T], data: str) -> T:
    try:
        parsed_data = model.model_validate_json(data)
    except ValidationError as e:
        raise ValidationError(
            f"Could not parse data into {model.__name__} object. Error: `{str(e)}`."
        )
    return parsed_data
