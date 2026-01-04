import asyncio
import copy
import struct
from typing import Final

from server.protocol.Client import Client
from server.protocol.TCP import TCPClient
from server.protocol.UDP import UDPProtocol
from server.requests.AbstractRequests import SimpleRequest
from server.requests.RequestTypes import RequestType
from shared.Helpers import Helpers
from shell.Logger import Logger


class APIServer:
    CRC32_CHECKSUM_LEN: Final[int] = 4
    DEFAULT_FLAGS: Final[dict[str, bool]] = {
        "e": False,
        "p": False,
        "g": False
    }

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

        client: TCPClient = TCPClient(reader, writer, this.aesKey, this, this.DEFAULT_FLAGS)
        asyncio.create_task(this.processRequest(msg, client))

    async def parsePacketInfo(this, msg: bytes) -> tuple[int, dict[str, bool]] | None:
        tLetter, zLetter, dataOffset = struct.unpack(">BBB", msg[0:3])
        if tLetter != ord("t") or zLetter != ord("z") or dataOffset < 3:
            return None

        packetFlags = copy.deepcopy(this.DEFAULT_FLAGS)

        flagsArray = set(msg[3:dataOffset])
        validFlags = packetFlags.keys()
        for flagInt in flagsArray:
            flag = chr(flagInt)
            if flag in validFlags:
                packetFlags[flag] = True
            else:
                return None

        return dataOffset, packetFlags

    async def respondToInvalid(this, msg: bytes, client: Client):
        if isinstance(client, TCPClient):
            protocol = "TCP"
        else:
            protocol = "UDP"

        Logger.log(f"Got an invalid {protocol} request: {msg}")
        Logger.log(client.flags)
        fakeJson: dict = {"requestType": "INVALID", "data": {"message": msg}}
        fakeJsonData: dict = fakeJson.pop("data")

        request = SimpleRequest(client, fakeJson, fakeJsonData, this.tzBot)
        await request.process()
        return

    async def processRequest(this, msg: bytes, client: Client) -> None:
        await this.tzBot.statsDb.addReceivedDataBandwidth(len(msg))

        if isinstance(client, TCPClient):
            protocol: str = "TCP"
        else:
            protocol: str = "UDP"

        await this.tzBot.statsDb.addProtocol(protocol)

        packetInfo: tuple[int, dict[str, bool]] | None = await this.parsePacketInfo(msg)
        if not packetInfo:
            await this.respondToInvalid(msg, client)
            return

        packetHeaderLen = packetInfo[0]
        packetFlags: dict[str, bool] = packetInfo[1]
        client.flags = packetFlags
        content = msg[packetHeaderLen:]

        appliedFlags = []

        # Process flags
        if packetFlags["e"]:
            decrypted = Helpers.AESDecrypt(content, this.aesKey)
            if not decrypted:
                client.flags = this.DEFAULT_FLAGS
                await this.respondToInvalid(content, client)
                return
            content = decrypted
            appliedFlags.append("encrypted")
        else:
            appliedFlags.append("unencrypted")

        if packetFlags["g"]:
            decompressed = Helpers.unGzip(content)
            if not decompressed:
                client.flags = this.DEFAULT_FLAGS
                await this.respondToInvalid(msg, client)
                return
            content = decompressed
            appliedFlags.append("GZIPped")

        if packetFlags["p"]:
            unpacked = Helpers.msgpackToJson(content)
            if not unpacked:
                client.flags = this.DEFAULT_FLAGS
                await this.respondToInvalid(msg, client)
                return
            content = unpacked
            appliedFlags.append("MSGPack")
        else:
            appliedFlags.append("JSON")

        jsonRequest: dict | None = await Helpers.parseJson(content.decode("utf-8", errors="ignore"))
        if not jsonRequest:
            client.flags = this.DEFAULT_FLAGS
            await this.respondToInvalid(content, client)
            return

        payload: dict = jsonRequest.pop("data", {})
        requestType: str = jsonRequest.get("requestType", "INVALID")

        try:
            reqType: RequestType = getattr(RequestType, requestType)
            await this.tzBot.statsDb.addEstablishedKnownRequestType(requestType)

            Logger.log(f"Got a known {protocol}, {", ".join(appliedFlags)} request: {content.decode()}")

            request = reqType(client, jsonRequest, payload, this.tzBot)
            await request.process()
        except AttributeError:
            Logger.log(f"Unknown RequestType: {requestType}")
            return
