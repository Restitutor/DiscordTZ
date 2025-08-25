import asyncio

from server.auth.AesKeys import getAesKeyByIp
from server.protocol.Client import Client
from server.ServerCrypto import AESEncrypt, RSAEncrypt


class UDPClient(Client):
    def __init__(this, transport: asyncio.DatagramTransport, ipAddress: tuple[str, int], aesKey: bytes) -> None:
        super().__init__(ipAddress, aesKey)
        this.transport: asyncio.DatagramTransport = transport

    def send(this, data: bytes) -> None:
        if this.encrypt:
            data = RSAEncrypt(data, this.rsaKey) if this.rsaKey is not None else AESEncrypt(data, this.aesKey)

        this.transport.sendto(data, this.ip)


class UDPProtocol(asyncio.DatagramProtocol):
    def __init__(this, server) -> None:  # noqa: ANN001
        this.server = server

    def connection_made(this, transport: asyncio.transports.DatagramTransport) -> None:
        this.transport = transport

    def datagram_received(this, data: bytes, addr: tuple[str, int]) -> None:
        client: UDPClient = UDPClient(this.transport, addr, getAesKeyByIp(addr[0]))
        asyncio.create_task(this.server.makeObject(data, client))
