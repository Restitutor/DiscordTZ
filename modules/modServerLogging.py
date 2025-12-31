import asyncio
import datetime
import io
import json

import discord
from discord.ext import commands
from typing_extensions import Final

from modules.TZBot import TZBot
from server.requests.AbstractRequests import SimpleRequest
from server.requests.Requests import UserIdUUIDLinkPost
from shared.Helpers import Helpers


class ServerLogging(commands.Cog):
    MAX_DATA_EMBED_LEN: Final[int] = 900
    def __init__(this, client: TZBot) -> None:
        this.client = client
        asyncio.create_task(this._postInit())

    async def _postInit(this) -> None:
        await this.client.wait_for("ready")
        SimpleRequest.commonEventHandler.onSuccess(this.onSuccess)
        SimpleRequest.commonEventHandler.onError(this.onError)

    async def createBasicEmbed(this, request: SimpleRequest, template: discord.Embed) -> tuple[discord.Embed, list[discord.File]] | tuple[None, None]:
        country = await Helpers.getCountryOrHost(request)

        await Helpers.tzBot.statsDb.addSentDataBandwidth(len(json.dumps(request.response.__dict__).encode('utf-8')))
        await Helpers.tzBot.statsDb.addRequestCountry(country)

        requestData: str = str(request.data)
        packetName: str = request.headers["requestType"]
        response: dict = {"message": request.response.message, "code": request.response.code}

        description = "\n".join([
                f"**Packet**: {packetName}",
                f"**Protocol**: {request.protocol}",
                f"**Source**: {'⚠️ ' + country + ' ⚠️' if country in {'CN', 'SG', 'HK', 'MO'} else country}",
            ])

        fileSendList: list[discord.File] = []

        if len(requestData) <= this.MAX_DATA_EMBED_LEN:
            template.add_field(name="Request Data", value=f"```{requestData}```", inline=False)
        else:
            template.add_field(name="Request Data", value="Request is included in the file below due to its size.", inline=False)
            requestFile = discord.File(io.BytesIO(requestData.encode("utf-8")), "requestdata.json")
            fileSendList.append(requestFile)


        if len(str(response)) <= this.MAX_DATA_EMBED_LEN:
            template.add_field(name="Response Data", value=f"```{response!s}```", inline=False)
        else:
            template.add_field(name="Response Data", value="Response is included in the file below due to its size.", inline=False)
            responseFile = discord.File(io.BytesIO(json.dumps(response).encode("utf-8")), "responsedata.json")
            fileSendList.append(responseFile)

        template.description = description
        template.timestamp = datetime.datetime.now()

        return template, fileSendList

    async def onError(this, request: SimpleRequest) -> None:
        lock = "🔒" if request.client.flags["e"] else ""
        embed: discord.Embed = discord.Embed(title=f"{lock} **Error** {lock}".strip(), color=discord.Color.red())
        embed, fileSendList = await this.createBasicEmbed(request, embed)

        await this.client.statsDb.addFailedRequest()
        if not embed:
            return

        if fileSendList:
            await this.client.errorChannel.send("", embed=embed, files=fileSendList)
            return

        await this.client.errorChannel.send("", embed=embed)

    async def onSuccess(this, request: SimpleRequest) -> None:
        if request.__class__.__name__ in {"PingRequest"}:
            return

        if isinstance(request, UserIdUUIDLinkPost):
            request.response.message = "<redacted>"

        lock = "🔒" if request.client.flags["e"] else ""
        embed: discord.Embed = discord.Embed(title=f"{lock} **Success** {lock}".strip(), color=discord.Color.green())
        embed, fileSendList = await this.createBasicEmbed(request, embed)

        await this.client.statsDb.addSuccessfulRequest()

        if not embed:
            return

        if fileSendList:
            await this.client.successChannel.send("", embed=embed, files=fileSendList)
            return

        await this.client.successChannel.send("", embed=embed)


def setup(client: TZBot) -> None:
    client.add_cog(ServerLogging(client))
