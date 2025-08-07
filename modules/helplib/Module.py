from dataclasses import dataclass

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class Argument:
    name: str
    type: str
    description: str
    required: bool
    defaultValue: str


@dataclass_json
@dataclass
class Command:
    requiredPerms: int
    name: str
    description: str
    help: str
    cooldown: int
    args: list[Argument]


@dataclass_json
@dataclass
class CommandGroup:
    name: str
    description: str
    commands: list[Command]

    def getCommandNames(this) -> list[str]:
        commands = []
        for command in this.commands:
            if (this.name != ""):
                commands.append(f"{this.name} {command.name}")
            else:
                commands.append(command.name)

        return commands


@dataclass_json
@dataclass
class Module:
    name: str
    cmdGroups: list[CommandGroup]

    def getCommandNames(this) -> list[str]:
        commands = []
        for group in this.cmdGroups:
            commands.extend(group.getCommandNames())

        return commands

    def getGroupNames(this) -> list[str]:
        groups = []
        for group in this.cmdGroups:
            if (group.name in {"", None}):
                continue
            groups.append(group.name)

        return groups
