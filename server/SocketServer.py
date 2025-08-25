import asyncio
import contextlib

from config.Config import ServerConfig
from database.DataDatabase import Database
from server.auth.AesKeys import getAesKeyByIp
from server.EventHandler import EventHandler
from server.protocol.Client import Client
from server.protocol.TCP import TCPClient
from server.protocol.UDP import UDPProtocol
from server.requests.Requests import SimpleRequest
from server.requests.RequestTypes import RequestType
from server.ServerCrypto import AESDecrypt
from shared.Helpers import parseJson
from shell.Logger import Logger


class SocketServer:
    serverConfig: ServerConfig
    db: Database
    eventHandler: EventHandler = EventHandler()

    def __init__(this, serverConfig: ServerConfig) -> None:
        this.serverConfig = serverConfig
        this.tcpClients: list[TCPClient] = []

    async def start(this) -> None:
        tcpServer = await asyncio.start_server(this.TCPInit, "0.0.0.0", int(this.serverConfig.port))
        loop = asyncio.get_running_loop()
        transport, protocol = await loop.create_datagram_endpoint(lambda: UDPProtocol(this), local_addr=("0.0.0.0", int(this.serverConfig.port)))
        this.protocol = protocol
        this.transport = transport
        try:
            async with tcpServer:
                Logger.success("Servers running!")
                await asyncio.Future()
        except asyncio.CancelledError:
            Logger.log("Servers shutting down!")
            transport.close()

    async def TCPInit(this, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            msg: bytes = await reader.read(65535)
        except Exception as e:  # noqa: BLE001
            Logger.error(f"Error reading from client: {e}")
            return

        for client in this.tcpClients:
            if client.ip == writer.get_extra_info("peername"):
                asyncio.create_task(this.makeObject(msg, client))
                return

        client: TCPClient = TCPClient(reader, writer, getAesKeyByIp(writer.get_extra_info("peername")))
        this.tcpClients.append(client)
        asyncio.create_task(this.makeObject(msg, client))

    async def makeObject(this, msg: bytes, client: Client) -> None:
        jsonRequest: dict | None = await parseJson(msg.decode("utf-8", errors="ignore"))

        if isinstance(client, TCPClient):
            protocol: str = "TCP"
        else:
            protocol: str = "UDP"

        if jsonRequest is not None:
            Logger.log(f"Got an unencrypted {protocol} request: {jsonRequest}")

        else:
            decrypted = AESDecrypt(msg, client.aesKey)
            jsonRequest = await parseJson(decrypted)

            if not jsonRequest:
                Logger.log(f"Got an invalid {protocol} request: {msg}")
                fakeJson: dict = {"requestType": "INVALID", "data": {"message": msg}}
                fakeJsonData: dict = fakeJson.pop("data")

                request = SimpleRequest(client, fakeJson, fakeJsonData)
                await request.process()

                return

            Logger.log(f"Got an encrypted {protocol} request: {jsonRequest}")
            client.encrypt = True

        payload: dict | None = jsonRequest.get("data", {})
        requestType: str | None = jsonRequest.get("requestType")

        if requestType:
            with contextlib.suppress(KeyError):
                jsonRequest.pop("data")

            try:
                reqType: RequestType = getattr(RequestType, requestType)
            except AttributeError:
                Logger.error(f"Invalid request type: {requestType}, defaulting to SimpleRequest")

                request = SimpleRequest(client, jsonRequest, payload)
                await request.process()
                return

            try:
                request = reqType(client, jsonRequest, payload)
                await request.process()

            except PermissionError as e:
                Logger.error(f"{e.args[0]}")
                SimpleRequest(client, jsonRequest, payload)
