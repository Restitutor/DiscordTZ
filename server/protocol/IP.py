from dataclasses import dataclass


@dataclass
class IP:
    def __init__(this, address: str, port: int) -> None:
        this.address = address
        this.port = port

    @classmethod
    def fromTuple(cls, ip: tuple[str, int]) -> "IP":
        return IP(ip[0], ip[1])
