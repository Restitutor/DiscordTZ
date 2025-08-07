import sys

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.layout import HSplit, Layout
from prompt_toolkit.widgets import TextArea

from shell.Commands import createCommandSystem
from shell.Logger import Logger


class Shell(Application):
    def __init__(this) -> None:
        Logger.setLogFunction(this.log)

        this.commandRegistry, this.commandContext = createCommandSystem(this)
        this.commandList = this.commandRegistry.getCommandNames()

        this.logLines: list[str] = []
        this.autoScroll = True
        this.logWindow = TextArea(scrollbar=True, wrap_lines=True, read_only=True, focusable=True)

        this.inputField = TextArea(
            height=1,
            prompt="Timezone Bot > ",
            multiline=False,
            read_only=False,
            focusable=True,
            accept_handler=this.cmdAcceptHandler,
            completer=WordCompleter(this.commandList, ignore_case=True),
            history=FileHistory(".tzhistory"),
        )

        this.layout = Layout(HSplit([this.logWindow, this.inputField]), focused_element=this.inputField)

        this.keyBindings = KeyBindings()
        this.keyBindings.add("c-up")(lambda event: this.layout.focus(this.logWindow))  # noqa: ARG005
        this.keyBindings.add("c-down")(lambda event: this.layout.focus(this.inputField))  # noqa: ARG005

        super().__init__(layout=this.layout, full_screen=True, key_bindings=this.keyBindings)

    def log(this, msg: str) -> None:
        this.logLines.append(msg)
        this.logWindow.text = "\n".join(this.logLines)
        this.invalidate()

        if this.autoScroll:
            this.logWindow.buffer.cursor_position = len(this.logWindow.text)

    def toggleAutoScroll(this, event: KeyPressEvent) -> None:  # noqa: ARG002
        this.autoScroll = not this.autoScroll
        if this.autoScroll:
            this.log("Autoscroll: ON")
            this.scrollToBottom()
        else:
            this.log("Autoscroll: OFF")

    def scrollToBottom(this) -> None:
        window = this.logWindow.window
        if window.render_info:
            maxScroll = max(0, window.render_info.content_height - window.render_info.window_height)
            window.vertical_scroll = maxScroll
            this.invalidate()

    def cmdAcceptHandler(this, buffer: Buffer) -> bool:
        text = buffer.text.strip()

        if not text:
            return True

        buffer.history.append_string(text)
        result = this.commandRegistry.executeCommand(text, this.commandContext)
        if not result.success and result.message:
            this.log(result.message)

        if result.shouldExit:
            sys.exit(result.exitCode)

        buffer.reset()
        return False
