import asyncio
import os
import stat
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import tzlocal
from discord import ExtensionAlreadyLoaded, ExtensionFailed, ExtensionNotFound, ExtensionNotLoaded, NoEntryPointError

from modules.TZBot import TZBot  # noqa: TC001
from shared import Graphs
from shared.Helpers import Helpers
from shell.Logger import Logger


@dataclass
class CommandResult:
    success: bool
    message: str | None = None
    shouldExit: bool = False
    exitCode: int = 0


class Command(ABC):
    name: str
    description: str
    aliases: list[str]

    def __init__(this, name: str, description: str = "", aliases: list[str] | None = None) -> None:
        this.name = name
        this.description = description
        this.aliases = aliases or []

    @abstractmethod
    async def execute(this, args: list[str], ctx: "CommandContext") -> CommandResult:
        pass

    def validateArgs(this, args: list[str]) -> bool:  # noqa: ARG002
        return True

    def getHelp(this) -> str:
        return f"{this.name}: {this.description}"


class CommandContext:
    shell: "Shell"
    variables: dict[Any, Any]

    def __init__(this, shell: "Shell") -> None:
        this.shell = shell
        this.variables = {}

    def log(this, message: str) -> None:
        Logger.log(message)

    def error(this, message: str) -> None:
        Logger.error(message)


# Built-in commands
class ExitCommand(Command):
    def __init__(this) -> None:
        super().__init__("exit", "Exit the shell with optional exit code", ["quit", "q", "stop"])

    async def execute(this, args: list[str], ctx: CommandContext) -> CommandResult:  # noqa: ARG002
        code = 0
        if args:
            if args[0].isdigit() or args[0].lstrip("-").isdigit():
                code = int(args[0])
            else:
                return CommandResult(False, f"Invalid exit code: {args[0]}")

        return CommandResult(True, f"Exiting with code {code}", shouldExit=True, exitCode=code)


class EchoCommand(Command):
    def __init__(this) -> None:
        super().__init__("echo", "Display a line of text")

    async def execute(this, args: list[str], ctx: CommandContext) -> CommandResult:
        message = " ".join(args) if args else ""
        ctx.log(message)
        return CommandResult(True)


class RestartCommand(Command):
    def __init__(this) -> None:
        super().__init__("restart", "Restart the shell")

    async def execute(this, args: list[str], ctx: CommandContext) -> CommandResult:  # noqa: ARG002
        ctx.log("Restarting the shell...")
        execPath = Path(sys.argv[0])

        try:
            os.execv(sys.argv[0], sys.argv)
        except OSError:
            try:
                oldMode = execPath.stat().st_mode
                oldPerms = stat.S_IMODE(oldMode)
                newPerms = oldPerms | 0o111  # Add execute permissions
                execPath.chmod(newPerms)
                os.execlp(sys.executable, sys.executable, *sys.argv)
            except (OSError, PermissionError) as execError:
                return CommandResult(False, f"Failed to restart: {execError}")

        return CommandResult(True)


class HelpCommand(Command):
    registry: "CommandRegistry"
    def __init__(this, registry: "CommandRegistry") -> None:
        super().__init__("help", "Show help for commands", ["h", "?"])
        this.registry = registry

    async def execute(this, args: list[str], ctx: CommandContext) -> CommandResult:
        if args and args[0]:
            commandName = args[0]
            command = this.registry.getCommand(commandName)
            if command:
                ctx.log(command.getHelp())
            else:
                return CommandResult(False, f"Unknown command: {commandName}")
        else:
            ctx.log("Available commands:")
            for cmdName in sorted(this.registry.commands.keys()):
                command = this.registry.commands[cmdName]
                aliases = f" (aliases: {', '.join(command.aliases)})" if command.aliases else ""
                ctx.log(f"  {command.name}{aliases} - {command.description}")

        return CommandResult(True)


class CommandRegistry:
    commands: dict[str, Command]
    aliases: dict[str, str]

    def __init__(this) -> None:
        this.commands: dict[str, Command] = {}
        this.aliases: dict[str, str] = {}
        this._setupBuiltins()

    def _setupBuiltins(this) -> None:
        builtinCommands = [
            ExitCommand(),
            EchoCommand(),
            RestartCommand(),
        ]

        for cmd in builtinCommands:
            this.register(cmd)

        helpCmd = HelpCommand(this)
        this.register(helpCmd)

    def register(this, command: Command) -> None:
        this.commands[command.name] = command

        for alias in command.aliases:
            this.aliases[alias] = command.name

    def unregister(this, commandName: str) -> bool:
        if commandName not in this.commands:
            return False

        command = this.commands[commandName]
        del this.commands[commandName]

        for alias in command.aliases:
            if alias in this.aliases:
                del this.aliases[alias]

        return True

    def getCommand(this, name: str) -> Command | None:
        if name in this.commands:
            return this.commands[name]

        if name in this.aliases:
            return this.commands[this.aliases[name]]

        return None

    def getCommandNames(this) -> list[str]:
        names = list(this.commands.keys())
        names.extend(this.aliases.keys())
        return sorted(names)

    async def executeCommand(this, commandLine: str, context: CommandContext) -> CommandResult:
        if not commandLine.strip():
            return CommandResult(True)

        parts = commandLine.strip().split()
        commandName = parts[0]
        args = parts[1:] if len(parts) > 1 else []

        command = this.getCommand(commandName)
        if not command:
            return CommandResult(False, f"Unknown command: {commandName}")

        if not command.validateArgs(args):
            return CommandResult(False, f"Invalid arguments for {commandName}")

        try:
            return await command.execute(args, context)
        except Exception as e:  # noqa: BLE001
            return CommandResult(False, f"Command execution failed: {e}")


def createCommandSystem(shellInstance: "Shell" = None) -> tuple[CommandRegistry, CommandContext]:
    registry = CommandRegistry()
    context = CommandContext(shellInstance)

    # Add custom commands
    # registry.register(DateCommand())

    return registry, context


# Additional commands
class Reload(Command):
    def __init__(this) -> None:
        super().__init__("reload", "Reloads a Discord bot module")

    async def execute(this, args: list[str], ctx: CommandContext) -> CommandResult:  # noqa: ARG002
        client: TZBot = Helpers.tzBot

        for arg in args:
            try:
                client.reload_extension(f"modules.mod{arg}")
                Logger.success(f"Module {arg} reloaded!")
            except (ExtensionNotFound, ExtensionNotLoaded, NoEntryPointError, ExtensionFailed) as e:
                Logger.error(f"Failed to reload module {arg}: {e}")

        asyncio.create_task(client.sync_commands())
        return CommandResult(True)

    def validateArgs(self, args: list[str]) -> bool:
        client: TZBot = Helpers.tzBot
        if len(args) < 1:
            return False

        toReload = [module for module in args if module in client.getLoadedModules()]
        return len(toReload) == len(args)


class Load(Command):
    def __init__(this) -> None:
        super().__init__("load", "Loads a Discord bot module")

    async def execute(this, args: list[str], ctx: CommandContext) -> CommandResult:  # noqa: ARG002
        client: TZBot = Helpers.tzBot

        try:
            await client.loadModules(args)
        except (ExtensionNotFound, ExtensionAlreadyLoaded, NoEntryPointError, ExtensionFailed) as e:
            Logger.error(e)

        asyncio.create_task(client.sync_commands())
        return CommandResult(True)

    def validateArgs(self, args: list[str]) -> bool:
        client: TZBot = Helpers.tzBot
        if len(args) < 1:
            return False

        toLoad = [module for module in args if module in client.getUnloadedModules()]
        return len(toLoad) == len(args)


class Unload(Command):
    def __init__(this) -> None:
        super().__init__("unload", "Unloads a Discord bot module")

    async def execute(this, args: list[str], ctx: CommandContext) -> CommandResult:  # noqa: ARG002
        client: TZBot = Helpers.tzBot

        try:
            await client.unloadModules(args)
        except (ExtensionNotFound, ExtensionNotLoaded) as e:
            Logger.error(e)

        return CommandResult(True)

    def validateArgs(self, args: list[str]) -> bool:
        client: TZBot = Helpers.tzBot
        if len(args) < 1:
            return False

        toUnload = [module for module in args if module in client.getLoadedModules()]
        return len(toUnload) == len(args)


class ModList(Command):
    def __init__(this) -> None:
        super().__init__("lsmod", "Lists all modules and their status", aliases=["ml", "ls"])

    async def execute(this, args: list[str], ctx: CommandContext) -> CommandResult:  # noqa: ARG002
        client: TZBot = Helpers.tzBot
        ctx.log("Module Status:")
        for module in client.getAvailableModules():
            ctx.log(f"{module}: {'Loaded' if module in client.getLoadedModules() else 'Unloaded'}")

        return CommandResult(True)

    def validateArgs(this, args: list[str]) -> bool:
        return len(args) == 0


class ForceSync(Command):
    def __init__(this) -> None:
        super().__init__("sync", "Force syncs to WSS")

    async def execute(this, args: list[str], ctx: CommandContext) -> CommandResult:  # noqa: ARG002
        client: TZBot = Helpers.tzBot

        asyncio.create_task(client.sync_commands(force=True))
        Logger.log("Force sync started.")

        return CommandResult(True)

    def validateArgs(this, args: list[str]) -> bool:
        return len(args) == 0

class ForceSaveStats(Command):
    def __init__(this) -> None:
        super().__init__("savestats", "Force saves current statistics")

    async def execute(this, args: list[str], ctx: CommandContext) -> CommandResult:  # noqa: ARG002
        client: TZBot = Helpers.tzBot

        asyncio.create_task(client.statsDb.dumpCurrent())
        Logger.log("Saving was successful!")

        return CommandResult(True)

    def validateArgs(this, args: list[str]) -> bool:
        return len(args) == 0

class Graph(Command):
    def __init__(this) -> None:
        super().__init__("graph", "Creates a graph from telemetry")

    async def execute(this, args: list[str], ctx: CommandContext) -> CommandResult:
        graphType = args[0] if len(args) >= 1 else "packetFailSuccessGraph"
        startTimestamp = datetime.fromtimestamp(int(args[1]), tzlocal.get_localzone()) if len(args) >= 2 and args[1].isnumeric() else None
        endTimestamp = datetime.fromtimestamp(int(args[2]), tzlocal.get_localzone()) if len(args) >= 3 and args[2].isnumeric() else None

        try:
            func = getattr(Graphs, graphType)
        except AttributeError:
            return CommandResult(False, f"Unknown graph type: {graphType}")

        await func(startTimestamp, endTimestamp)
        Logger.success("Graph created!")

        return CommandResult(True)

    def validateArgs(this, args: list[str]) -> bool:
        return len(args) <= 3