from collections.abc import Iterator
from dataclasses import dataclass


@dataclass
class IP:
    def __init__(this, address: str, port: int) -> None:
        this.address = address
        this.port = port

    def __iter__(this) -> Iterator["IP"]:
        for key in this.__dict__:
            yield this.__dict__[key]

    @classmethod
    def fromTuple(cls, ip: tuple[str, int]) -> "IP":
        return IP(ip[0], ip[1])
