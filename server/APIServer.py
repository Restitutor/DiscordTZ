import asyncio

from server.ServerCrypto import AESDecrypt
from server.protocol.Client import Client
from server.protocol.TCP import TCPClient
from server.protocol.UDP import UDPProtocol
from server.requests.RequestTypes import RequestType
from server.requests.Requests import SimpleRequest
from shared.Helpers import Helpers
from shell.Logger import Logger


class APIServer:
    protocol: UDPProtocol
    transport: asyncio.DatagramTransport

    def __init__(this, tzBot: "TZBot") -> None:
        this.tzBot = tzBot
        this.db = tzBot.db
        this.serverConfig = tzBot.config.server
        this.aesKey: bytes = this.serverConfig.aesKey.encode()

    async def start(this) -> None:
        Logger.log("Starting API Server...")
        tcpServer = await asyncio.start_server(this.TCPReceived, "0.0.0.0", int(this.serverConfig.port))

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

    async def TCPReceived(this, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            msg: bytes = await reader.read(65535)
        except Exception as e:  # noqa: BLE001
            Logger.error(f"Error reading from client: {e}")
            return

        client: TCPClient = TCPClient(reader, writer, this.aesKey)
        asyncio.create_task(this.processRequest(msg, client))

    async def processRequest(this, msg: bytes, client: Client) -> None:
        await this.tzBot.statsDb.addReceivedDataBandwidth(len(msg))
        jsonRequest: dict | None = await Helpers.parseJson(msg.decode("utf-8", errors="ignore"))

        if isinstance(client, TCPClient):
            protocol: str = "TCP"
        else:
            protocol: str = "UDP"

        await this.tzBot.statsDb.addProtocol(protocol)

        if jsonRequest:
            Logger.log(f"Got an unencrypted {protocol} request: {jsonRequest}")
            client.aesKey = None

        else:
            decrypted = AESDecrypt(msg, this.aesKey)
            jsonRequest = await Helpers.parseJson(decrypted)

            if not jsonRequest:
                client.aesKey = None
                Logger.log(f"Got an invalid {protocol} request: {msg}")
                fakeJson: dict = {"requestType": "INVALID", "data": {"message": msg}}
                fakeJsonData: dict = fakeJson.pop("data")

                request = SimpleRequest(client, fakeJson, fakeJsonData, this.tzBot)
                await request.process()

                return

            Logger.log(f"Got an encrypted {protocol} request: {jsonRequest}")
            client.encrypt = True

        payload: dict = jsonRequest.pop("data", {})
        requestType: str = jsonRequest.get("requestType", "INVALID")

        try:
            reqType: RequestType = getattr(RequestType, requestType)
        except AttributeError:
            Logger.error(f"Invalid request type: {requestType}, defaulting to SimpleRequest")

            request = SimpleRequest(client, jsonRequest, payload, this.tzBot)
            await request.process()
            return

        await this.tzBot.statsDb.addEstablishedKnownRequestType(requestType)
        request = reqType(client, jsonRequest, payload, this.tzBot)
        await request.process()
