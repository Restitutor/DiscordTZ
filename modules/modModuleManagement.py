import asyncio
from pathlib import Path

import discord
from discord.ext import commands

from modules.TZBot import TZBot
from shell.Logger import Logger


class ModuleManagement(commands.Cog):
    modulesGroup = discord.SlashCommandGroup(name="modules", description="Modules related stuff", checks=[commands.is_owner()])

    def __init__(this, client: TZBot) -> None:
        this.client = client
        asyncio.create_task(this.client.sync_commands())

    async def getModules(this, ctx: discord.AutocompleteContext = None) -> list[str]:
        if ctx is not None and not await ctx.bot.is_owner(ctx.interaction.user):
            return []
        results: list[str] = [
            file.name[:-3] for file in Path.iterdir(Path("./modules")) if (file.name.startswith("mod") and file.name.endswith(".py"))
        ]

        return results

    async def getUnloadedModules(this, ctx: discord.AutocompleteContext = None) -> list[str]:
        results: list[str] = await this.getModules(ctx)
        filtered: list[str] = []
        loaded = [module.replace("modules.mod", "") for module in list(this.client.extensions.keys())]
        for result in results:
            if result.replace("mod", "") in loaded:
                continue
            filtered.append(result.replace("mod", ""))

        if ctx is not None and ctx.value not in {None, ""}:
            filtered = [entry for entry in filtered if entry.lower().startswith(ctx.value.lower())]
        return filtered

    async def getLoadedModules(this, ctx: discord.AutocompleteContext = None) -> list[str]:
        if ctx is not None and not await ctx.bot.is_owner(ctx.interaction.user):
            return []

        loaded = [module.replace("modules.mod", "") for module in list(this.client.extensions.keys())]
        if ctx is not None and ctx.value not in {None, ""}:
            loaded = [entry for entry in loaded if entry.lower().startswith(ctx.value.lower())]

        return loaded

    @modulesGroup.command(name="load", description="Loads a specific module.")
    @commands.is_owner()
    async def loadModule(
        this, ctx: discord.ApplicationContext, modulename: discord.Option(str, "The module you want to load", autocomplete=getUnloadedModules)
    ) -> None:
        if modulename not in await this.getUnloadedModules():
            await ctx.response.send_message(f"Module {modulename} doesn't exist!", ephemeral=True)
            Logger.error(f"{ctx.user.name} tried to load {modulename}, which doesn't exist!")
            return

        this.client.load_extension(f"modules.mod{modulename}")
        Logger.success(f"{ctx.user.name} loaded {modulename}!")
        asyncio.create_task(this.client.sync_commands())
        await ctx.response.send_message(f"Module {modulename} loaded!", ephemeral=True)

    @modulesGroup.command(name="unload", description="Unloads a specific module.")
    @commands.is_owner()
    async def unloadModule(
        this, ctx: discord.ApplicationContext, modulename: discord.Option(str, "The module you want to unload", autocomplete=getLoadedModules)
    ) -> None:
        if modulename not in await this.getLoadedModules():
            await ctx.response.send_message(f"Module {modulename} doesn't exist!", ephemeral=True)
            Logger.error(f"{ctx.user.name} tried to unload {modulename}, which doesn't exist!")
            return

        this.client.unload_extension(f"modules.mod{modulename}")
        Logger.success(f"{ctx.user.name} unloaded {modulename}!")
        asyncio.create_task(this.client.sync_commands())
        await ctx.response.send_message(f"Module {modulename} unloaded!", ephemeral=True)

    @modulesGroup.command(name="reload", description="Reloads a specific module.")
    @commands.is_owner()
    async def reloadModule(
        this, ctx: discord.ApplicationContext, modulename: discord.Option(str, "The module you want to reload", autocomplete=getLoadedModules)
    ) -> None:
        if modulename not in await this.getLoadedModules():
            await ctx.response.send_message(f"Module {modulename} doesn't exist!", ephemeral=True)
            Logger.error(f"{ctx.user.name} tried to reload {modulename}, which doesn't exist!")
            return

        this.client.reload_extension(f"modules.mod{modulename}")
        Logger.success(f"{ctx.user.name} reloaded {modulename}!")
        asyncio.create_task(this.client.sync_commands())
        await ctx.response.send_message(f"Module {modulename} reloaded!", ephemeral=True)

    @loadModule.error
    @unloadModule.error
    @reloadModule.error
    async def moduleError(this, ctx: discord.ApplicationContext, error: Exception) -> None:
        await ctx.response.send_message("You do not have the required permissions.", ephemeral=True)
        Logger.error(f"{ctx.user.name} tried to mess with modules. Error: {error}")


def setup(client: TZBot) -> None:
    client.add_cog(ModuleManagement(client))
