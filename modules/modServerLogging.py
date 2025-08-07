import asyncio
import datetime

import discord
from discord.ext import commands

from modules.TZBot import TZBot
from server.requests.AbstractRequests import SimpleRequest
from server.requests.Requests import UserIdUUIDLinkPost
from shared import Helpers


def createBasicEmbed(request: SimpleRequest, template: discord.Embed) -> tuple[discord.Embed, list[discord.File]] | tuple[None, None]:
    if request.__class__.__name__ in {"PingRequest", "HelloRequest", "KeyRenewRequest"}:
        return (None, None)

    hosts = Helpers.getHosts()

    if request.city is not None:
        country = request.city.country.iso_code
    elif request.client.ipAddress[0] == "127.0.0.1":
        with open("/etc/hostname") as f:
            country = f.read().capitalize()
    elif request.client.ipAddress[0] in hosts:
        country = hosts[request.client.ipAddress[0]].capitalize()
    else:
        country = "Local"

    requestData: str = str(request.data)
    packetName: str = request.headers["requestType"]
    response: dict = {"message": request.response[1], "code": request.response[0]}

    description = "\n".join(
        [
            f"**Packet**: {packetName}",
            f"**Protocol**: {request.protocol}",
            f"**Source**: {'⚠️ ' + country + ' ⚠️' if country in {'CN', 'SG', 'HK', 'MO'} else country}",
        ]
    )

    fileSendList: list[discord.File] = []

    maxDataEmbedLen = 900
    if len(requestData) <= maxDataEmbedLen:
        template.add_field(name="Request Data", value=f"```{requestData}```", inline=False)
    else:
        template.add_field(name="Request Data", value="Request is included in the file below due to its size.", inline=False)
        with open("request.txt", "w") as file:
            file.write(requestData)

        with open("request.txt", "rb") as file:
            requestFile = discord.File(file)
            fileSendList.append(requestFile)

    if len(str(response)) <= maxDataEmbedLen:
        template.add_field(name="Response Data", value=f"```{response!s}```", inline=False)
    else:
        template.add_field(name="Response Data", value="Response is included in the file below due to its size.", inline=False)

        with open("response.txt", "w") as file:
            file.write(str(response))
        with open("response.txt", "rb") as file:
            responseFile = discord.File(file)
            fileSendList.append(responseFile)

    template.description = description
    template.timestamp = datetime.datetime.now()

    return (template, fileSendList)


class ServerLogging(commands.Cog):
    def __init__(this, client: TZBot) -> None:
        this.client = client
        asyncio.create_task(this.client.sync_commands())
        asyncio.create_task(this._postInit())

    async def _postInit(this) -> None:
        await this.client.wait_for("ready")
        SimpleRequest.commonEventHandler.onSuccess(this.onSuccess)
        SimpleRequest.commonEventHandler.onError(this.onError)

    async def onError(this, request: SimpleRequest) -> None:
        lock = "🔒" if request.client.encrypt else ""
        embed: discord.Embed = discord.Embed(title=f"{lock} **Error** {lock}", color=discord.Color.red())
        embed, fileSendList = createBasicEmbed(request, embed)
        if embed is None:
            return

        if fileSendList != []:
            await this.client.errorChannel.send("", embed=embed, files=fileSendList)
            return

        await this.client.errorChannel.send("", embed=embed)

    async def onSuccess(this, request: SimpleRequest) -> None:
        if isinstance(request, UserIdUUIDLinkPost):
            this.client.linkCodes.update({request.code: (request.uuid, request.timezone)})
            request.response[1] = "<redacted>"
            asyncio.create_task(this.client.removeCode(15, request.code))

        lock = "🔒" if request.client.encrypt else ""
        embed: discord.Embed = discord.Embed(title=f"{lock} **Success** {lock}", color=discord.Color.green())
        embed, fileSendList = createBasicEmbed(request, embed)

        if embed is None:
            return

        if fileSendList:
            await this.client.successChannel.send("", embed=embed, files=fileSendList)
            return

        await this.client.successChannel.send("", embed=embed)


def setup(client: TZBot) -> None:
    client.add_cog(ServerLogging(client))
