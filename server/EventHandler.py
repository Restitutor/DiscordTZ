import asyncio


class EventHandler:
    def __init__(self):
        self.initErrorCallbacks = []
        self.initSuccessCallbacks = []

    def onError(self, callback):
        self.initErrorCallbacks.append(callback)

    def onSuccess(self, callback):
        self.initSuccessCallbacks.append(callback)

    def triggerError(self, instance):
        for callback in self.initErrorCallbacks:
            asyncio.create_task(callback(instance))

    def triggerSuccess(self, instance):
        for callback in self.initSuccessCallbacks:
            asyncio.create_task(callback(instance))
