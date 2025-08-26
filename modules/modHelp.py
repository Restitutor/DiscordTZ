import contextlib
from textwrap import dedent

import aiofiles
import discord
from discord.ext import commands

from modules.helplib.Module import Module
from modules.TZBot import TZBot


class Help(commands.Cog):
    helpGroup = discord.SlashCommandGroup("help", description="Shows different kinds of command help.")

    def __init__(this, client: TZBot) -> None:
        this.client = client
        with open("help.json") as f:
            this.commandHelp: list[Module] = Module.schema().loads(f.read(), many=True)

        this.moduleList = [module.name for module in this.commandHelp]
        this.groupList = [cmdGroup.name for module in this.commandHelp for cmdGroup in module.cmdGroups if cmdGroup.name != ""]
        this.commandList = [dedent(name) for module in this.commandHelp for name in module.getCommandNames()]

    async def commandAutocomplete(this, ctx: discord.AutocompleteContext) -> list[str]:
        async with aiofiles.open("help.json") as f:
            this.commandHelp: list[Module] = Module.schema().loads(await f.read(), many=True)

        this.commandList = [dedent(name) for module in this.commandHelp for name in module.getCommandNames()]
        return [command for command in this.commandList if command.lower().startswith(ctx.value.lower())]

    async def groupAutocomplete(this, ctx: discord.AutocompleteContext) -> list[str]:
        async with aiofiles.open("help.json") as f:
            this.commandHelp: list[Module] = Module.schema().loads(await f.read(), many=True)

        this.groupList = [cmdGroup.name for module in this.commandHelp for cmdGroup in module.cmdGroups if cmdGroup.name != ""]
        return [group for group in this.groupList if group != "" and group.lower().startswith(ctx.value.lower())]

    async def moduleAutocomplete(this, ctx: discord.AutocompleteContext) -> list[str]:
        async with aiofiles.open("help.json") as f:
            this.commandHelp: list[Module] = Module.schema().loads(await f.read(), many=True)

        this.moduleList = [module.name for module in this.commandHelp]
        return [module for module in this.moculeList if module.lower().startswith(ctx.value.lower())]

    @helpGroup.command(name="commands", description="Shows you available commands/help with a specific command.")
    async def commands(
        this,
        ctx: discord.ApplicationContext,
        commandname: discord.Option(
            str, "Command name to display help for. If left empty, shows a list of commands.", required=False, autocomplete=commandAutocomplete
        ) = None,
    ) -> None:
        async with aiofiles.open("help.json") as f:
            this.commandHelp = Module.schema().loads(await f.read(), many=True)

        if commandname is None:
            embed = discord.Embed(title="**Command List**", description="", color=discord.Color.green())

            for module in this.commandHelp:
                for cmdGroup in module.cmdGroups:
                    embed.description += f"\n**{module.name}\n**"
                    if cmdGroup.name != "":
                        embed.description += f"  __{cmdGroup.name}__\n"
                        embed.description += "    \n".join(cmdGroup.getCommandNames())
                    else:
                        embed.description += "  \n".join(cmdGroup.getCommandNames())

            await ctx.response.send_message(embed=embed)
            return
        if isinstance(commandname, str) and commandname in this.commandList:
            embed = discord.Embed(title=f"**Command Help for /{commandname}**", description="", color=discord.Color.green())

            for module in this.commandHelp:
                if commandname not in module.getCommandNames():
                    continue

                for cmdGroup in module.cmdGroups:
                    if commandname not in cmdGroup.getCommandNames():
                        continue

                    for command in cmdGroup.commands:
                        with contextlib.suppress(IndexError):
                            if command.name != commandname or command.name != commandname.split(" ")[1]:
                                continue

                        embed.add_field(
                            name="**Command Info**",
                            value="\n".join(
                                [
                                    f"Module: `{module.name}`{f'\nGroup: `{cmdGroup.name}`' if cmdGroup.name != '' else ''}",
                                    f"Command: `/{commandname}`",
                                    f"Description: `{command.description}`",
                                    f"Cooldown: `{command.cooldown}s`",
                                    f"Permissions: `{command.requiredPerms}`",
                                ]
                            ),
                            inline=False,
                        )

                        embed.add_field(name="**Command Info**", value=command.help + "\n", inline=False)

                        argsUsage: list[str] = []
                        if command.args:
                            argsHelp: list[str] = []
                            for arg in command.args:
                                argsUsage.append(f"<{arg.name}: {arg.type}>" if arg.required else f"({arg.name}: {arg.type})")
                                argsHelp.append(
                                    "\n".join(
                                        [
                                            f"Name: `{arg.name}`",
                                            f"Description: `{arg.description}`",
                                            f"Type: `{arg.type}`",
                                            f"Required: `{arg.required}` {f'\nDefault: `{arg.defaultValue}`\n' if not arg.required else '\n'}",
                                        ]
                                    )
                                )

                            embed.add_field(name="**Arguments**", value="----------\n".join(argsHelp), inline=False)

                        embed.add_field(
                            name="**Usage**",
                            value=f"<> = required; () = optional\n\
                        ```/{commandname} {' '.join(argsUsage)}```",
                            inline=False,
                        )

                        await ctx.response.send_message(embed=embed)
                        return

        else:
            embed = this.client.fail.copy()
            embed.description = "Invalid command."
            await ctx.response.send_message(embed=embed)
            return

    @helpGroup.command(name="groups", description="Shows you help for a specific command group.")
    async def groups(
        this,
        ctx: discord.ApplicationContext,
        groupname: discord.Option(str, "Command Group name to display help for.", autocomplete=groupAutocomplete),
    ) -> None:
        if groupname in this.groupList:
            embed = discord.Embed(title=f"**Group help for /{groupname}**", description="", color=discord.Color.green())

            for module in this.commandHelp:
                if groupname not in module.getGroupNames():
                    continue

                for cmdGroup in module.cmdGroups:
                    if groupname != cmdGroup.name:
                        continue

                    embed.add_field(
                        name="**Group Info**",
                        value="\n".join(
                            [
                                f"Module: `{module.name}`",
                                f"Group: `{cmdGroup.name}`",
                            ]
                        ),
                        inline=False,
                    )

                    commandHelpList = ["<> = required; () = optional\n "]
                    for command in cmdGroup.commands:
                        argsUsage: list[str] = []
                        if command.args:
                            argsUsage.extend(f"<{arg.name}: {arg.type}>" if arg.required else f"({arg.name}: {arg.type})" for arg in command.args)

                        commandHelpList.append(
                            "\n".join(
                                [
                                    f"/{groupname + ' ' + command.name}: {command.description}",
                                    f"```/{groupname + ' ' + command.name} {' '.join(argsUsage)}```",
                                ]
                            )
                        )

                    embed.add_field(name="**Commands**", value="\n".join(commandHelpList), inline=False)
                    await ctx.response.send_message(embed=embed)
                    return
        else:
            embed = this.client.fail.copy()
            embed.description = "Invalid group."
            await ctx.response.send_message(embed=embed)
            return


def setup(client: TZBot) -> None:
    client.add_cog(Help(client))
