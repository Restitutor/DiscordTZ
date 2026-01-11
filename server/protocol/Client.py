from server.protocol.APIPayload import PacketFlags
from server.protocol.IP import IP
from shared.Helpers import Helpers


class Client:
    def __init__(this, ipAddress: tuple[str, int], aesKey: bytes, flags: PacketFlags, server: "APIServer") -> None:
        this.ip: IP = IP.fromTuple(ipAddress)
        this.aesKey = aesKey
        this.flags = flags
        this.server = server

    async def _applyFlags(this, data: bytes):
        if this.flags & PacketFlags.MSGPACK:
            data = Helpers.jsonToMsgpack(data)
        if this.flags & PacketFlags.GUNZIP:
            data = Helpers.compressGzip(data)
        if this.flags & PacketFlags.CHACHAPOLY:
            data = Helpers.ChaCha20Encrypt(data, this.aesKey)
        elif this.flags & PacketFlags.AESGCM:
            data = Helpers.AESEncrypt(data, this.aesKey)

        # Pattern + headerLen + flags + contentLen
        headerLen = 2 + 1 + 1 + 2
        header = b"tz" + headerLen.to_bytes(1, "big", signed=False) + this.flags.to_bytes(1, "big", signed=False) + len(data).to_bytes(2, "big", signed=False)
        return header + data

    async def send(this, data: bytes) -> None:
        pass

    async def close(this) -> None:
        pass
