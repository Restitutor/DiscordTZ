import os
import stat
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from shell.Logger import Logger


@dataclass
class CommandResult:
    success: bool
    message: str | None = None
    shouldExit: bool = False
    exitCode: int = 0


class Command(ABC):
    def __init__(this, name: str, description: str = "", aliases: list[str] | None = None) -> None:
        this.name = name
        this.description = description
        this.aliases = aliases or []

    @abstractmethod
    def execute(this, args: list[str], ctx: "CommandContext") -> CommandResult:
        pass

    def validateArgs(this, args: list[str]) -> bool:  # noqa: ARG002
        return True

    def getHelp(this) -> str:
        return f"{this.name}: {this.description}"


class CommandContext:
    def __init__(this, shellInstance) -> None:  # noqa: ANN001
        this.shell = shellInstance
        this.variables = {}

    def log(this, message: str) -> None:
        Logger.log(message)

    def error(self, message: str) -> None:
        Logger.error(message)


# Built-in commands
class ExitCommand(Command):
    def __init__(this) -> None:
        super().__init__("exit", "Exit the shell with optional exit code", ["quit", "q"])

    def execute(this, args: list[str], ctx: CommandContext) -> CommandResult:  # noqa: ARG002
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

    def execute(this, args: list[str], ctx: CommandContext) -> CommandResult:
        message = " ".join(args) if args else ""
        ctx.log(message)
        return CommandResult(True)


class RestartCommand(Command):
    def __init__(this) -> None:
        super().__init__("restart", "Restart the shell")

    def execute(this, args: list[str], ctx: CommandContext) -> CommandResult:  # noqa: ARG002
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
                os.execv(sys.argv[0], sys.argv)
            except (OSError, PermissionError) as execError:
                return CommandResult(False, f"Failed to restart: {execError}")

        return CommandResult(True)


class ClearCommand(Command):
    def __init__(this) -> None:
        super().__init__("clear", "Clear the terminal/log area", ["cls"])

    def execute(this, args: list[str], ctx: CommandContext) -> CommandResult:  # noqa: ARG002
        if ctx.shell and hasattr(ctx.shell, "logWindow"):
            ctx.shell.logWindow.buffer.text = ""
            ctx.shell.logLines = []
        return CommandResult(True, "Screen cleared")


class HelpCommand(Command):
    def __init__(this, registry: "CommandRegistry") -> None:
        super().__init__("help", "Show help for commands", ["h", "?"])
        this.registry = registry

    def execute(this, args: list[str], ctx: CommandContext) -> CommandResult:
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
    def __init__(this) -> None:
        this.commands: dict[str, Command] = {}
        this.aliases: dict[str, str] = {}
        this._setupBuiltins()

    def _setupBuiltins(this) -> None:
        builtinCommands = [
            ExitCommand(),
            EchoCommand(),
            RestartCommand(),
            ClearCommand(),
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

    def executeCommand(this, commandLine: str, context: CommandContext) -> CommandResult:
        if not commandLine.strip():
            return CommandResult(True)

        parts = commandLine.strip().split()
        command_name = parts[0]
        args = parts[1:] if len(parts) > 1 else []

        command = this.getCommand(command_name)
        if not command:
            return CommandResult(False, f"Unknown command: {command_name}")

        if not command.validateArgs(args):
            return CommandResult(False, f"Invalid arguments for {command_name}")

        try:
            return command.execute(args, context)
        except Exception as e:  # noqa: BLE001
            return CommandResult(False, f"Command execution failed: {e}")


def createCommandSystem(shellInstance=None) -> tuple[CommandRegistry, CommandContext]:  # noqa: ANN001
    registry = CommandRegistry()
    context = CommandContext(shellInstance)

    # Add custom commands
    # registry.register(DateCommand())

    return registry, context
