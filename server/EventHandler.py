import asyncio
from collections.abc import Callable


class EventHandler:
    def __init__(this) -> None:
        this.initErrorCallbacks: list[Callable] = []
        this.initSuccessCallbacks: list[Callable] = []

    def onError(this, callback: Callable) -> None:
        this.initErrorCallbacks.append(callback)

    def onSuccess(this, callback: Callable) -> None:
        this.initSuccessCallbacks.append(callback)

    def triggerError(this, instance) -> None:  # noqa: ANN001
        for callback in this.initErrorCallbacks:
            asyncio.create_task(callback(instance))

    def triggerSuccess(this, instance) -> None:  # noqa: ANN001
        for callback in this.initSuccessCallbacks:
            asyncio.create_task(callback(instance))
