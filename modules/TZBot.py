import asyncio
import contextlib
import json
from pathlib import Path

import aiofiles
import discord
import geoip2
from discord.ext import commands
from geoip2 import database  # noqa: F401

from config.Config import Config
from database.APIKeyDatabase import ApiKeyDatabase
from database.DataDatabase import Database
from shared import Helpers
from shell.Logger import Logger


class TZBot(commands.Bot):
    loadedExtensions: list[str] = []

    def __init__(this, config: Config, **kwargs) -> None:
        super().__init__(**kwargs)
        this.config = config

        Helpers.tzBot = this

        this.ownerId = this.config.ownerId
        this.linkCodes: dict[str, tuple[str, str]] = {}
        this.db: Database = Database(this.config.mariadbDetails)
        this.apiDb = ApiKeyDatabase(this.config.server.apiKeysKey)
        this.maxMindDb: geoip2.database.Reader = geoip2.database.Reader("GeoLite2-City.mmdb")

        try:
            with open("dialogOwners.json") as f:
                this.dialogOwners: list[int] = json.loads(f.read())
        except json.JSONDecodeError:
            this.dialogOwners: list[int] = []

        this.success: discord.Embed = discord.Embed(title="**Success!**", description="The operation was successful!", color=discord.Color.green())
        this.fail: discord.Embed = discord.Embed(
            title="**Something went wrong.**", description="There was an error in the operation.", color=discord.Color.red()
        )

    async def on_connect(this) -> None:
        await this.loadCogs()

        this.errorChannel = await asyncio.create_task(this.fetch_channel(this.config.packetLogs.errorChannelId))
        this.successChannel = await asyncio.create_task(this.fetch_channel(this.config.packetLogs.successChannelId))

    async def on_ready(this) -> None:
        Logger.success("Discord Bot is online!")

    async def loadCogs(this) -> None:
        for file in Path.iterdir(Path("./modules")):
            if file.name.startswith("mod") and file.name.endswith(".py"):
                this.loadedExtensions.extend(this.load_extension(f"modules.{file.name[:-3]}"))

        this.loadedExtensions = [extension.replace("modules.mod", "") for extension in this.loadedExtensions]
        Logger.success(f"Modules {', '.join(this.loadedExtensions)} loaded!")

    async def removeCode(this, delay: int, code: str) -> None:
        await asyncio.sleep(delay * 60)
        with contextlib.suppress(KeyError):
            this.linkCodes.pop(code)

    async def addOwner(this, userId: int) -> None:
        if userId in this.dialogOwners:
            return

        this.dialogOwners.append(userId)
        async with aiofiles.open("dialogOwners.json", "w") as f:
            await f.write(json.dumps(this.dialogOwners))

    async def removeOwner(this, userId: int) -> None:
        with contextlib.suppress(ValueError):
            this.dialogOwners.remove(userId)
            async with aiofiles.open("dialogOwners.json", "w") as f:
                await f.write(json.dumps(this.dialogOwners))
