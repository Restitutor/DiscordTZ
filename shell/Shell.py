import asyncio
import sys

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.layout import HSplit, Layout
from prompt_toolkit.widgets import TextArea

from shell.Commands import ForceSync, Load, ModList, Reload, Unload, createCommandSystem, ForceSaveStats, Graph, \
    CommandRegistry, CommandContext
from shell.Logger import Logger


class Shell(Application):
    commandRegistry: CommandRegistry
    commandContext: CommandContext
    commandList: list[str]

    logLines: list[str]
    autoscroll: bool

    logWindow: TextArea
    inputField: TextArea
    layout: Layout
    keyBindings: KeyBindings

    def __init__(this) -> None:
        Logger.setLogFunction(this.log)

        this.commandRegistry, this.commandContext = createCommandSystem(this)
        this.commandList = this.commandRegistry.getCommandNames()

        this.commandRegistry.register(Reload())
        this.commandRegistry.register(Load())
        this.commandRegistry.register(Unload())
        this.commandRegistry.register(ModList())
        this.commandRegistry.register(ForceSync())
        this.commandRegistry.register(ForceSaveStats())
        this.commandRegistry.register(Graph())

        this.logLines: list[str] = []
        this.autoScroll = True
        this.logWindow = TextArea(scrollbar=True, wrap_lines=True, read_only=True, focusable=True)

        this.inputField = TextArea(
            height=1,
            prompt="Timezone Bot > ",
            multiline=False,
            read_only=False,
            focusable=True,
            accept_handler=this.acceptor,
            completer=WordCompleter(this.commandList, ignore_case=True),
            history=FileHistory(".tzhistory"),
        )

        this.layout = Layout(HSplit([this.logWindow, this.inputField]), focused_element=this.inputField)

        this.keyBindings = KeyBindings()
        this.keyBindings.add("c-up")(lambda event: this.layout.focus(this.logWindow))  # noqa: ARG005
        this.keyBindings.add("c-down")(this.switchToInput)
        this.keyBindings.add("c-l")(this.clearScreen)

        super().__init__(layout=this.layout, full_screen=True, key_bindings=this.keyBindings)

    def log(this, msg: str) -> None:
        window = this.logWindow.window
        if window.render_info:
            trailingLinesRemoved = 0
            while this.logLines and this.logLines[-1] == "":
                this.logLines.pop()
                trailingLinesRemoved += 1

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

    def switchToInput(this, event: KeyPressEvent) -> None:  # noqa: ARG002
        this.layout.focus(this.inputField)
        window = this.logWindow.window
        if window.render_info:
            this.logWindow.buffer.cursor_position = len(this.logWindow.text)
            this.invalidate()

    def clearScreen(this, event: KeyPressEvent) -> None:  # noqa: ARG002
        window = this.logWindow.window
        if window.render_info:
            while this.logLines and this.logLines[-1] == "":
                this.logLines.pop()

            this.logLines.extend([""] * window.render_info.window_height)
            this.logWindow.text = "\n".join(this.logLines)

            this.logWindow.buffer.cursor_position = len(this.logWindow.text)

            this.invalidate()

    def scrollToBottom(this) -> None:
        window = this.logWindow.window
        if window.render_info:
            maxScroll = max(0, window.render_info.content_height - window.render_info.window_height)
            window.vertical_scroll = maxScroll
            this.invalidate()

    def acceptor(this, buffer: Buffer | str) -> bool:
        text = buffer.text.strip() if isinstance(buffer, Buffer) else buffer
        buffer.history.append_string(text)

        asyncio.create_task(this.cmdAcceptHandler(text))
        buffer.reset()
        return False

    async def cmdAcceptHandler(this, text: str) -> None:
        result = await this.commandRegistry.executeCommand(text, this.commandContext)
        if not result.success and result.message:
            Logger.error(result.message)

        if result.shouldExit:
            sys.exit(result.exitCode)
