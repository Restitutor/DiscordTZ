import datetime

from shell.Shell import log


class Logger:
    @staticmethod
    def log(message: object) -> None:
        timeNow: str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        log(f"[{timeNow}] [LOG] {message}")

    @staticmethod
    def error(message: object) -> None:
        timeNow: str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        log(f"[{timeNow}] [ERROR] {message}")

    @staticmethod
    def success(message: object) -> None:
        timeNow: str = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        log(f"[{timeNow}] [SUCCESS] {message}")
