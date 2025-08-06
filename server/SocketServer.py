import asyncio
import json

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
    serverSettings: dict
    db: Database
    eventHandler: EventHandler = EventHandler()
    tcpClients: list[TCPClient] = []

    def __init__(this):
        with open("config.json") as f:
            this.serverSettings = json.loads(f.read())["server"]

    async def start(this):
        tcpServer = await asyncio.start_server(this.TCPInit, "0.0.0.0", int(this.serverSettings["port"]))
        loop = asyncio.get_running_loop()
        transport, protocol = await loop.create_datagram_endpoint(lambda: UDPProtocol(this), local_addr=("0.0.0.0", int(this.serverSettings["port"])))
        this.protocol = protocol
        this.transport = transport
        try:
            async with tcpServer:
                Logger.log("Servers running!")
                await asyncio.Future()
        except asyncio.CancelledError:
            Logger.log("Servers shutting down!")
            transport.close()

    async def TCPInit(this, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            msg: bytes = await reader.read(65535)
        except Exception as e:
            Logger.error(f"Error reading from client: {e}")
            return

        for client in this.tcpClients:
            if client.ipAddress == writer.get_extra_info("peername"):
                asyncio.create_task(this.makeObject(msg, client))
                return

        client: TCPClient = TCPClient(reader, writer, getAesKeyByIp(writer.get_extra_info("peername")))
        this.tcpClients.append(client)
        asyncio.create_task(this.makeObject(msg, client))

    async def makeObject(this, msg: bytes, client: Client) -> None:
        jsonRequest: dict | None = parseJson(msg.decode("utf-8", errors="ignore"))

        if isinstance(client, TCPClient):
            protocol: str = "TCP"
        else:
            protocol: str = "UDP"

        if jsonRequest is not None:
            Logger.log(f"Got an unencrypted {protocol} request: {jsonRequest}")

        else:
            decrypted = AESDecrypt(msg, client.aesKey)
            jsonRequest = parseJson(decrypted)
            if jsonRequest is None:
                Logger.log(f"Got an invalid {protocol} request: {msg}")
                fakeJson: dict = {"requestType": "INVALID", "data": {"message": msg}}
                fakeJsonData: dict = fakeJson.pop("data")
                SimpleRequest(client, fakeJson, fakeJsonData)
                return
            else:
                Logger.log(f"Got an encrypted {protocol} request: {jsonRequest}")
                client.encrypt = True

        if ("requestType", "data" in jsonRequest):  # noqa: F634
            member = str(jsonRequest["requestType"])
            try:
                reqType: RequestType = getattr(RequestType, member)
            except AttributeError:
                Logger.error(f"Invalid request type: {str(jsonRequest['requestType'])}, defaulting to SimpleRequest")
                jsonData = jsonRequest.pop("data")
                SimpleRequest(client, jsonRequest, jsonData)
                return

            jsonData = jsonRequest.pop("data")
            try:
                reqType(client, jsonRequest, jsonData)
            except PermissionError as e:
                Logger.error(f"{e.args[0]}")
                SimpleRequest(client, jsonRequest, jsonData)
