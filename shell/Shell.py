# --- Core Imports ---
import os
import stat
import sys
from pathlib import Path

from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.layout import HSplit, Layout
from prompt_toolkit.widgets import TextArea


# --- Command Registry ---
def cmdExit(args: list[str]) -> None:
    code = int(args[0]) if args and args[0].isalnum() else 0
    sys.exit(code)


def cmdEcho(args: list[str]) -> None:
    message = " ".join(args) if args else "No message provided."
    log(message)


def cmdRestart(args: list[str]) -> None:  # noqa: ARG001
    log("Restarting the shell...")
    execPath: Path = Path(sys.argv[0])
    try:
        os.execv(sys.argv[0], sys.argv)
    except OSError:
        oldMode = Path.stat(execPath).st_mode
        oldPerms = stat.S_IMODE(oldMode)

        newPerms = oldPerms | 0o111  # Equivalent to +x

        Path.chmod(execPath, newPerms)
        os.execv(sys.argv[0], sys.argv)


def cmdClear(args: list[str]) -> None:  # noqa: ARG001
    logArea.buffer.text = ""


command_registry = {
    "exit": cmdExit,
    "echo": cmdEcho,
    "restart": cmdRestart,
    "clear": cmdClear,
}

# --- Log and Input ---
logArea = TextArea(scrollbar=False, wrap_lines=True, read_only=False, focusable=False)

inputField = TextArea(height=1, prompt="Timezone Bot > ", multiline=False)


def log(message: object) -> None:
    logArea.buffer.insert_text(str(message) + "\n")


def parseAndExec(userInput: str) -> None:
    parts = userInput.strip().split()
    if not parts:
        return

    command = parts[0].lower()
    args = parts[1:]

    handler = command_registry.get(command)
    if handler:
        handler(args)
    else:
        log(f"Unknown command: '{command}'")


# --- Key Bindings ---
kb = KeyBindings()


@kb.add("enter")
def onEnter(event: KeyPressEvent) -> None:
    userInput = inputField.text
    parseAndExec(userInput)
    inputField.text = ""
    event.app.layout.focus(inputField)


# --- Layout and App ---
layout = Layout(HSplit([logArea, inputField]), focused_element=inputField)

app = Application(layout=layout, key_bindings=kb, full_screen=True)


async def startShell() -> None:
    await app.run_async()
