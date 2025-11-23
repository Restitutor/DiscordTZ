from dataclasses import dataclass
from typing import Literal

from discord import Option


@dataclass
class Command:
    prefix: Literal["/", "tz!"]

    name: str
    description: str
    cooldown: float | None
    checks: list
    args: list[Option]
    mention: str

    def isOwnerCommand(this) -> bool:
        for check in this.checks:
            if str(check.__qualname__).startswith("is_owner"):
                return True

        return False