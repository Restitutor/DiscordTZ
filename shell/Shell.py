# --- Core Imports ---
import os
import stat
import sys
from pathlib import Path

from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout
from prompt_toolkit.widgets import TextArea


# --- Command Registry ---
def cmd_exit(args):
    code = int(args[0]) if args and args[0].isalnum() else 0
    exit(code)


def cmd_echo(args):
    message = " ".join(args) if args else "No message provided."
    log(message)


def cmd_restart(args):
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


def cmd_clear(args):
    log_area.buffer.text = ""


command_registry = {
    "exit": cmd_exit,
    "echo": cmd_echo,
    "restart": cmd_restart,
    "clear": cmd_clear,
}

# --- Log and Input ---
log_area = TextArea(scrollbar=False, wrap_lines=True, read_only=False, focusable=False)

input_field = TextArea(height=1, prompt="Timezone Bot > ", multiline=False)


def log(message):
    log_area.buffer.insert_text(message + "\n")


def parse_and_execute(user_input):
    parts = user_input.strip().split()
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
def on_enter(event):
    user_input = input_field.text
    parse_and_execute(user_input)
    input_field.text = ""
    event.app.layout.focus(input_field)


# --- Layout and App ---
layout = Layout(HSplit([log_area, input_field]), focused_element=input_field)

app = Application(layout=layout, key_bindings=kb, full_screen=True)


async def startShell():
    await app.run_async()
