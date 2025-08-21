import discord
from discord.ext import commands

from modules.TZBot import TZBot
from shell.Logger import Logger


class ModuleManagement(commands.Cog):
    modulesGroup = discord.SlashCommandGroup(name="modules", description="Modules related stuff", checks=[commands.is_owner()])

    def __init__(this, client: TZBot) -> None:
        this.client = client

    async def getUnloadedModules(this, ctx: discord.AutocompleteContext = None) -> list[str]:
        if not await ctx.bot.is_owner(ctx.interaction.user):
            return []

        return [module for module in this.client.getUnloadedModules() if module.lower().startswith(ctx.value.lower())]

    async def getLoadedModules(this, ctx: discord.AutocompleteContext = None) -> list[str]:
        if not await ctx.bot.is_owner(ctx.interaction.user):
            return []

        return [module for module in this.client.getLoadedModules() if module.lower().startswith(ctx.value.lower())]

    @modulesGroup.command(name="load", description="Loads a specific module.")
    @commands.is_owner()
    async def loadModule(
        this, ctx: discord.ApplicationContext, modulename: discord.Option(str, "The module you want to load", autocomplete=getUnloadedModules)
    ) -> None:
        if modulename not in this.client.getUnloadedModules():
            await ctx.response.send_message(f"Module {modulename} doesn't exist!", ephemeral=True)
            Logger.error(f"{ctx.user.name} tried to load {modulename}, which doesn't exist!")
            return

        await this.client.loadModules([modulename])
        Logger.success(f"{ctx.user.name} loaded {modulename}!")

        await ctx.response.send_message(f"Module {modulename} loaded!", ephemeral=True)

    @modulesGroup.command(name="unload", description="Unloads a specific module.")
    @commands.is_owner()
    async def unloadModule(
        this, ctx: discord.ApplicationContext, modulename: discord.Option(str, "The module you want to unload", autocomplete=getLoadedModules)
    ) -> None:
        if modulename not in this.client.getLoadedModules():
            await ctx.response.send_message(f"Module {modulename} doesn't exist!", ephemeral=True)
            Logger.error(f"{ctx.user.name} tried to unload {modulename}, which doesn't exist!")
            return

        await this.client.unloadModules([modulename])
        Logger.success(f"{ctx.user.name} unloaded {modulename}!")

        await ctx.response.send_message(f"Module {modulename} unloaded!", ephemeral=True)

    @modulesGroup.command(name="reload", description="Reloads a specific module.")
    @commands.is_owner()
    async def reloadModule(
        this, ctx: discord.ApplicationContext, modulename: discord.Option(str, "The module you want to reload", autocomplete=getLoadedModules)
    ) -> None:
        if modulename not in this.client.getLoadedModules():
            await ctx.response.send_message(f"Module {modulename} doesn't exist!", ephemeral=True)
            Logger.error(f"{ctx.user.name} tried to reload {modulename}, which doesn't exist!")
            return

        await this.client.reloadModules([modulename])
        Logger.success(f"{ctx.user.name} reloaded {modulename}!")

        await ctx.response.send_message(f"Module {modulename} reloaded!", ephemeral=True)

    @loadModule.error
    @unloadModule.error
    @reloadModule.error
    async def moduleError(this, ctx: discord.ApplicationContext, error: commands.CommandError) -> None:
        await ctx.response.send_message("You do not have the required permissions.", ephemeral=True)
        Logger.error(f"{ctx.user.name} tried to mess with modules. Error: {error}")


def setup(client: TZBot) -> None:
    client.add_cog(ModuleManagement(client))
