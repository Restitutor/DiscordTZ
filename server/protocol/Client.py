import struct

from server.protocol.IP import IP
from shared.Helpers import Helpers


class Client:
    def __init__(this, ipAddress: tuple[str, int], aesKey: bytes, flags: dict[str, bool], server: "APIServer") -> None:
        this.ip: IP = IP.fromTuple(ipAddress)
        this.aesKey = aesKey
        this.flags = flags
        this.server = server

    async def _applyFlags(this, data: bytes):
        usedFlags = ""
        if this.flags["p"]:
            data = Helpers.jsonToMsgpack(data)
            usedFlags += "p"
        if this.flags["g"]:
            data = Helpers.compressGzip(data)
            usedFlags += "g"
        if this.flags["e"]:
            data = Helpers.AESEncrypt(data, this.aesKey)
            usedFlags += "e"

        headerLen = 3 + len(usedFlags)
        header = b"tz" + struct.pack(">B", headerLen) + usedFlags.encode()
        return header + data

    async def send(this, data: bytes) -> None:
        pass

    async def close(this) -> None:
        pass
