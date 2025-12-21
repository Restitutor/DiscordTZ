import asyncio

from server.ServerCrypto import AESEncrypt
from server.protocol.Client import Client


class UDPClient(Client):
    def __init__(this, transport: asyncio.DatagramTransport, ipAddress: tuple[str, int], aesKey: bytes) -> None:
        super().__init__(ipAddress, aesKey)
        this.transport: asyncio.DatagramTransport = transport

    async def send(this, data: bytes) -> None:
        if this.aesKey:
            data = AESEncrypt(data, this.aesKey)

        this.transport.sendto(data, tuple(this.ip))


class UDPProtocol(asyncio.DatagramProtocol):
    def __init__(this, server: "APIServer") -> None:  # noqa: ANN001
        this.server = server

    def connection_made(this, transport: asyncio.transports.DatagramTransport) -> None:
        this.transport = transport

    def datagram_received(this, data: bytes, addr: tuple[str, int]) -> None:
        client: UDPClient = UDPClient(this.transport, addr, this.server.aesKey)
        asyncio.create_task(this.server.processRequest(data, client))
