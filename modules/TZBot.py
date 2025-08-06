import asyncio
import contextlib
import json
from pathlib import Path

import discord
import geoip2
from discord.ext import commands
from geoip2 import database  # noqa: F401

from database.APIKeyDatabase import ApiKeyDatabase
from database.DataDatabase import Database
from shared import Helpers
from shell.Logger import Logger


class TZBot(commands.Bot):
    loadedExtensions: list[str] = []

    def __init__(this, **options):
        super().__init__(**options)

        Helpers.tzBot = this

        with open("config.json") as f:
            this.config: dict = json.loads(f.read())

        this.ownerId = this.config["ownerId"]
        this.linkCodes: dict[str, tuple[str, str]] = {}
        this.db: Database = Database(this.config.get("mariadbDetails"))
        this.apiDb = ApiKeyDatabase(this.config)
        this.maxMindDb: geoip2.database.Reader = geoip2.database.Reader("GeoLite2-City.mmdb")

        try:
            with open("dialogOwners.json") as f:
                this.dialogOwners: list[int] = json.loads(f.read())
        except Exception:
            this.dialogOwners: list[int] = []

        this.success: discord.Embed = discord.Embed(title="**Success!**", description="The operation was successful!", color=discord.Color.green())

        this.fail: discord.Embed = discord.Embed(
            title="**Something went wrong.**", description="There was an error in the operation.", color=discord.Color.red()
        )

    async def on_connect(this):
        await this.loadCogs()

        this.errorChannel = await asyncio.create_task(this.fetch_channel(this.config["packetLogs"]["errorChannelId"]))
        this.successChannel = await asyncio.create_task(this.fetch_channel(this.config["packetLogs"]["successChannelId"]))

    async def on_ready(this):
        Logger.success("Discord Bot is online!")
        Helpers.ownerId = (await this.application_info()).owner.id

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

    def addOwner(this, userId: int) -> None:
        this.dialogOwners.append(userId)
        with open("dialogOwners.json", "w") as f:
            f.write(json.dumps(this.dialogOwners))

    def removeOwner(this, userId: int) -> None:
        with contextlib.suppress(ValueError):
            this.dialogOwners.remove(userId)
            with open("dialogOwners.json", "w") as f:
                f.write(json.dumps(this.dialogOwners))
