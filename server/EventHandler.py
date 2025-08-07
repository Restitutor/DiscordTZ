import asyncio
from collections.abc import Callable


class EventHandler:
    def __init__(this) -> None:
        this.initErrorCallbacks: list[Callable] = []
        this.initSuccessCallbacks: list[Callable] = []

    def onError(this, instance: Callable) -> None:
        this.initErrorCallbacks.append(instance)

    def onSuccess(this, instance: Callable) -> None:
        this.initSuccessCallbacks.append(instance)

    def triggerError(this, instance: Callable) -> None:
        for callback in this.initErrorCallbacks:
            asyncio.create_task(callback(instance))

    def triggerSuccess(this, instance: Callable) -> None:
        for callback in this.initSuccessCallbacks:
            asyncio.create_task(callback(instance))
