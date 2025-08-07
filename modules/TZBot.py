import asyncio
import contextlib
import json
import pathlib

import aiofiles
import discord
import geoip2
from discord import ExtensionAlreadyLoaded, ExtensionFailed, ExtensionNotFound, ExtensionNotLoaded, NoEntryPointError
from discord.ext import commands
from geoip2 import database  # noqa: F401

from config.Config import Config
from database.APIKeyDatabase import ApiKeyDatabase
from database.DataDatabase import Database
from shared import Helpers
from shell.Logger import Logger


class TZBot(commands.Bot):
    loadedModules: list[str] = []

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

    # WSS shit
    async def on_connect(this) -> None:
        await this.loadCogs()

        this.errorChannel = await asyncio.create_task(this.fetch_channel(this.config.packetLogs.errorChannelId))
        this.successChannel = await asyncio.create_task(this.fetch_channel(this.config.packetLogs.successChannelId))

    async def on_ready(this) -> None:
        Logger.success("Discord Bot is online!")

    # Modules shit
    def getAvailableModules(this) -> list[str]:
        return [file.stem[3:] for file in pathlib.Path("./modules").glob("mod*.py") if file.stem.startswith("mod")]

    def getLoadedModules(this) -> list[str]:
        return this.loadedModules

    def getUnloadedModules(this) -> list[str]:
        return [module for module in this.getAvailableModules() if module not in this.loadedModules]

    def unloadModules(this, modules: list[str]) -> None:
        for module in modules:
            if module not in this.getLoadedModules():
                asyncio.create_task(this.sync_commands(force=True))
                raise ExtensionNotLoaded(f"Module {module} is not loaded")

            try:
                this.unload_extension(f"modules.mod{module}")
                this.loadedModules.remove(module)
                Logger.success(f"Module {module} unloaded!")
            except (ExtensionNotFound, ExtensionNotLoaded) as e:
                Logger.error(f"Failed to unload module {module}: {e}")
                raise e  # noqa: TRY201
            finally:
                asyncio.create_task(this.sync_commands(force=True))

    def loadModules(this, modules: list[str]) -> None:
        for module in modules:
            if module not in this.getUnloadedModules():
                asyncio.create_task(this.sync_commands(force=True))
                raise ExtensionAlreadyLoaded(f"Module {module} is loaded")

            try:
                this.load_extension(f"modules.mod{module}")
                this.loadedModules.append(module)
                Logger.success(f"Module {module} loaded!")
            except (ExtensionNotFound, ExtensionAlreadyLoaded, NoEntryPointError, ExtensionFailed) as e:
                Logger.error(f"Failed to load module {module}: {e}")
                raise e  # noqa: TRY201
            finally:
                asyncio.create_task(this.sync_commands(force=True))

    def reloadModules(this, modules: list[str]) -> None:
        for module in modules:
            if module not in this.getLoadedModules():
                asyncio.create_task(this.sync_commands(force=True))
                raise ExtensionNotLoaded(f"Module {module} is not loaded")

            try:
                this.reload_extension(f"modules.mod{module}")
                Logger.success(f"Module {module} reloaded!")
            except (ExtensionNotFound, ExtensionNotLoaded, NoEntryPointError, ExtensionFailed) as e:
                Logger.error(f"Failed to reload module {module}: {e}")
                raise e  # noqa: TRY201
            finally:
                asyncio.create_task(this.sync_commands(force=True))

    async def loadCogs(this) -> None:
        this.loadedModules.extend(
            [ext.split(".")[1][3:] for module in this.getAvailableModules() for ext in this.load_extension(f"modules.mod{module}")]
        )
        Logger.success(f"Modules {', '.join(this.loadedModules)} loaded!")

    # Persistent UI shit
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

    # Verification code invalidifier
    async def removeCode(this, delay: int, code: str) -> None:
        await asyncio.sleep(delay * 60)
        with contextlib.suppress(KeyError):
            this.linkCodes.pop(code)
