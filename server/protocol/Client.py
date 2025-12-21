from Crypto.PublicKey import RSA

from server.protocol.IP import IP


class Client:

    def __init__(this, ipAddress: tuple[str, int], aesKey: bytes) -> None:
        this.ip: IP = IP.fromTuple(ipAddress)
        this.aesKey = aesKey

    async def send(this, data: bytes) -> None:
        pass

    async def close(this) -> None:
        pass
