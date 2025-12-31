import asyncio
from typing import TypedDict, Any, Literal, Union
import ipaddress

from server.ServerCrypto import AESDecrypt
from server.protocol.Client import Client
from server.protocol.TCP import TCPClient
from server.protocol.UDP import UDPProtocol
from server.requests.RequestTypes import RequestType
from server.requests.Requests import SimpleRequest
from shared.Helpers import Helpers
from shell.Logger import Logger


# TODO: These fields need more detail
class TimezoneRequestData(TypedDict):
    userId: int

class TimezonePayload(TypedDict):
    requestType: Literal["TIMEZONE_FROM_USERID"]
    data: TimezoneRequestData

class IPRequestData(TypedDict):
    ip: str

class IPPayload(TypedDict):
    requestType: Literal["TIMEZONE_FROM_IP"]
    data: IPRequestData

class PingRequestData(TypedDict):
    pass

class PingPayload(TypedDict):
    requestType: Literal["PING"]
    data: PingRequestData

class LinkPostRequestData(TypedDict):
    uuid: str
    timezone: str

class LinkPostPayload(TypedDict):
    requestType: Literal["USER_ID_UUID_LINK_POST"]
    data: LinkPostRequestData

class UUIDRequestData(TypedDict):
    uuid: str

class UUIDPayload(TypedDict):
    requestType: Literal["TIMEZONE_FROM_UUID", "IS_LINKED", "USER_ID_FROM_UUID"]
    data: UUIDRequestData

APIPayload = Union[TimezonePayload, IPPayload, PingPayload, LinkPostPayload, UUIDPayload]


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
        jsonRequest: APIPayload | None = await Helpers.parseJson(msg.decode("utf-8", errors="ignore"))

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

        if isinstance(jsonRequest, dict) and "requestType" in jsonRequest:
             reqTypeStr = jsonRequest.get("requestType")
             payload = jsonRequest.get("data", {})
             
             # if elif chain is verbose but more type safe
             if reqTypeStr == "TIMEZONE_FROM_USERID":
                 await RequestType.TIMEZONE_FROM_USERID(client, jsonRequest, payload, this.tzBot).process()
             elif reqTypeStr == "TIMEZONE_FROM_IP":
                 await RequestType.TIMEZONE_FROM_IP(client, jsonRequest, payload, this.tzBot).process()
             elif reqTypeStr == "PING":
                 await RequestType.PING(client, jsonRequest, payload, this.tzBot).process()
             elif reqTypeStr == "USER_ID_UUID_LINK_POST":
                 await RequestType.USER_ID_UUID_LINK_POST(client, jsonRequest, payload, this.tzBot).process()
             elif reqTypeStr == "TIMEZONE_FROM_UUID":
                 await RequestType.TIMEZONE_FROM_UUID(client, jsonRequest, payload, this.tzBot).process()
             elif reqTypeStr == "IS_LINKED":
                 await RequestType.IS_LINKED(client, jsonRequest, payload, this.tzBot).process()
             elif reqTypeStr == "USER_ID_FROM_UUID":
                 await RequestType.USER_ID_FROM_UUID(client, jsonRequest, payload, this.tzBot).process()
             else:
                 Logger.error(f"Invalid request type: {reqTypeStr}, defaulting to SimpleRequest")
                 request = SimpleRequest(client, jsonRequest, payload, this.tzBot)
                 await request.process()
             
             await this.tzBot.statsDb.addEstablishedKnownRequestType(str(reqTypeStr))
             return

        # Fallback if structure doesn't match expected dict (should be handled by parseJson returning dict)

