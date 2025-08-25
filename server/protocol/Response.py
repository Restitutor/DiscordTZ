from dataclasses import dataclass
from typing import Any


@dataclass
class Response:
    code: int
    message: Any

    def __init__(this, code: int, message: Any) -> None:  # noqa: ANN401
        this.code = code
        this.message = message
