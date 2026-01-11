import asyncio
import contextlib
from asyncio import Queue
from typing import Final

from server.protocol.APIPayload import PacketFlags
from server.protocol.Client import Client


class UDPClient(Client):
    def __init__(this, transport: asyncio.DatagramTransport, ipAddress: tuple[str, int], aesKey: bytes, server: "APIServer", flags: PacketFlags = 0) -> None:
        super().__init__(ipAddress, aesKey, flags, server)
        this.transport: asyncio.DatagramTransport = transport

    async def send(this, data: bytes) -> None:
        finalData = await this._applyFlags(data)
        this.transport.sendto(finalData, tuple(this.ip))


class UDPProtocol(asyncio.DatagramProtocol):
    PROCESS_TASK: Final[asyncio.Task[None]]
    _STOP_EVENT: Final[asyncio.Event]

    def __init__(this, server: "APIServer") -> None:  # noqa: ANN001
        this.server = server
        this.transport: asyncio.transports.DatagramTransport | None = None
        this.requestQueue: Queue[tuple[bytes, UDPClient]] = Queue()

        this.PROCESS_TASK = asyncio.create_task(this.processQueue())
        this._STOP_EVENT = asyncio.Event()

    def connection_made(this, transport: asyncio.transports.DatagramTransport) -> None:
        this.transport = transport

    def datagram_received(this, data: bytes, addr: tuple[str, int]) -> None:
        if not data.startswith(b"tz"):
            return

        this.requestQueue.put_nowait((data, UDPClient(this.transport, addr, this.server.aesKey, this.server)))

    def close(this):
        this.transport.close()
        this.requestQueue.empty()
        with contextlib.suppress(asyncio.CancelledError, TypeError):
            this._STOP_EVENT.set()
            this.PROCESS_TASK.done()

    async def processQueue(this):
        while True:
            done, pending = await asyncio.wait(
                {
                    asyncio.create_task(this.requestQueue.get()),
                    asyncio.create_task(this._STOP_EVENT.wait()),
                },
                return_when=asyncio.FIRST_COMPLETED,
            )

            if this._STOP_EVENT.is_set():
                break

            task = done.pop()
            data, client = task.result()
            await this.server.processRequest(data, client)
