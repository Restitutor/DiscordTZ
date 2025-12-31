from dataclasses import dataclass
from typing import Any, TypeVar, Generic, Literal

T = TypeVar("T")

ValidStatusCode = Literal[200, 400, 403, 404, 405, 409, 500]

@dataclass
class Response(Generic[T]):
    code: ValidStatusCode
    message: T

    def __init__(this, code: ValidStatusCode, message: T) -> None:  # noqa: ANN401
        this.code = code
        this.message = message
