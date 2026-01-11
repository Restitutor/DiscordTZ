from enum import IntEnum
from typing import Self

class PacketFlags(IntEnum):
    AESGCM = 1 << 0
    CHACHAPOLY = 1 << 1
    GUNZIP = 1 << 2
    MSGPACK = 1 << 3

class APIPayload:
    dataOffset: int
    requestType: int
    flags: PacketFlags
    contentLen: int

    def __init__(this, dataOffset: int, requestType: int, flags: PacketFlags, contentLen: int) -> None:
        this.dataOffset = dataOffset
        this.requestType = requestType
        this.flags = flags
        this.contentLen = contentLen

    @classmethod
    def fromTuple(cls, apiPayload: tuple[int, int, int, int, int]) -> Self:
        return cls(*apiPayload)