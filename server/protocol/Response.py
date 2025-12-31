from dataclasses import dataclass
from typing import Any


@dataclass
class Response:
    code: int
    message: str | int

    def __init__(this, code: int, message: str | int) -> None:  # noqa: ANN401
        this.code = code
        this.message = message
