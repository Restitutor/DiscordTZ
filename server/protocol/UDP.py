import asyncio

from server.protocol.Client import Client


class UDPClient(Client):
    def __init__(this, transport: asyncio.DatagramTransport, ipAddress: tuple[str, int], aesKey: bytes, server: "APIServer", flags: dict[str, bool] = None) -> None:
        super().__init__(ipAddress, aesKey, flags, server)
        this.transport: asyncio.DatagramTransport = transport

    async def send(this, data: bytes) -> None:
        finalData = await this._applyFlags(data)
        this.transport.sendto(finalData, tuple(this.ip))


class UDPProtocol(asyncio.DatagramProtocol):
    def __init__(this, server: "APIServer") -> None:  # noqa: ANN001
        this.server = server

    def connection_made(this, transport: asyncio.transports.DatagramTransport) -> None:
        this.transport = transport

    def datagram_received(this, data: bytes, addr: tuple[str, int]) -> None:
        client: UDPClient = UDPClient(this.transport, addr, this.server.aesKey, this.server, this.server.DEFAULT_FLAGS)
        asyncio.create_task(this.server.processRequest(data, client))
