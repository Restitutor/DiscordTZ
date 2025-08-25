from Crypto.PublicKey import RSA

from server.protocol.IP import IP


class Client:
    rsaKey: RSA.RsaKey | None = None
    aesKey: bytes | None = None

    def __init__(this, ipAddress: tuple[str, int], aesKey: bytes) -> None:
        this.ip: IP = IP.fromTuple(ipAddress)
        this.aesKey: bytes = aesKey
        this.encrypt = False

    def send(this, data: bytes) -> None:
        pass

    def close(this) -> None:
        pass
