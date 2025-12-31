from dataclasses import dataclass
from typing import Any, TypeVar, Generic

T = TypeVar("T")

@dataclass
class Response(Generic[T]):
    code: int
    message: T

    def __init__(this, code: int, message: T) -> None:  # noqa: ANN401
        this.code = code
        this.message = message
