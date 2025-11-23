import datetime
from collections.abc import Callable
from typing import ClassVar


class Logger:
    _logFunc: ClassVar[Callable] = print

    @classmethod
    def setLogFunction(cls, logFunc: Callable) -> None:
        cls._logFunc = logFunc

    @staticmethod
    def log(message: object) -> None:
        timeNow: str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        Logger._logFunc(f"[{timeNow}] [LOG] {message}")

    @staticmethod
    def error(message: object) -> None:
        timeNow: str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        Logger._logFunc(f"[{timeNow}] [ERROR] {message}")

    @staticmethod
    def success(message: object) -> None:
        timeNow: str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        Logger._logFunc(f"[{timeNow}] [SUCCESS] {message}")

    @staticmethod
    def warning(message: object) -> None:
        timeNow: str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        Logger._logFunc(f"[{timeNow}] [WARNING] {message}")
