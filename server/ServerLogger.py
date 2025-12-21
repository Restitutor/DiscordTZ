import io
import json
from datetime import datetime
from typing import Final

import discord

from server.requests.AbstractRequests import SimpleRequest
from shared.Helpers import Helpers


class ServerLogger:
    MAX_DATA_EMBED_LEN: Final[int] = 900
    def __init__(this, tzBot: "TZBot", loggingEnabled: bool) -> None:
        this.tzBot = tzBot
        this.loggingEnabled = loggingEnabled

    async def setLoggingEnabled(this, enabled: bool) -> None:
        this.loggingEnabled = enabled

    async def sendLogEmbed(this, request: SimpleRequest) -> None:
        if request.__class__.__name__ in {"PingRequest"}:
            return

        embed: discord.Embed = discord.Embed()
        fileSendList: list[discord.File] = []

        if request.__class__.__name__ in {"TimeZoneFromIPRequest"}:
            request.data["ip"] = "<redacted>"

        if request.__class__.__name__ in {"UserIdUUIDLinkPost"}:
            request.response.message = "<redacted>"

        if len(str(request.data)) < this.MAX_DATA_EMBED_LEN:
            embed.add_field(name="Request Data", value=f"```{json.dumps(request.data)}```", inline=False)
        else:
            embed.add_field(name="Request Data", value=f"Request is included in the file below due to its size.", inline=False)
            requestFile = discord.File(io.BytesIO(json.dumps(request.data).encode("utf-8")), "RequestData.json")
            fileSendList.append(requestFile)

        if len(str(request.response)) < this.MAX_DATA_EMBED_LEN:
            embed.add_field(name="Response Data", value=f"```{json.dumps(request.response.__dict__)}```", inline=False)
        else:
            embed.add_field(name="Response Data", value=f"Request is included in the file below due to its size.", inline=False)
            responseFile = discord.File(io.BytesIO(json.dumps(request.response.__dict__).encode("utf-8")), "ResponseData.json")
            fileSendList.append(responseFile)

        lock = "🔒" if request.client.aesKey else ""
        warning = "⚠️" if request.city.country.iso_code in Helpers.BLACKLISTED_COUNTRIES else ""

        packetName: str = request.headers["requestType"]
        protocol: str = request.protocol
        source: str = f"{warning} {await Helpers.getCountryOrHost(request)} {warning}".strip()

        description = "\n".join([
            f"**Packet**: {packetName}",
            f"**Protocol**: {protocol}",
            f"**Source**: {source}",
        ])

        embed.description = description
        embed.timestamp = datetime.now()

        if 200 <= request.response.code <= 300:
            embed.colour = discord.Color.green()
            embed.title = f"{lock} **Success** {lock}".strip()
            await this.tzBot.successChannel.send(embed=embed, files=fileSendList)

        else:
            embed.colour = discord.Color.red()
            embed.title = f"{lock} **Error** {lock}".strip()
            await this.tzBot.errorChannel.send(embed=embed, files=fileSendList)

