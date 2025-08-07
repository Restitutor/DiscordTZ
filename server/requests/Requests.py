import base64
import subprocess
from pathlib import Path

import geoip2.errors
from Crypto.PublicKey import RSA

from server.Api import ApiPermissions
from server.protocol.Client import Client
from server.requests.AbstractRequests import AliasRequest, APIRequest, SimpleRequest, UserIdRequest, UUIDRequest
from server.ServerError import ErrorCode
from shared import Helpers, Timezones
from shared.Timezones import checkList
from shell import Shell
from shell.Logger import Logger


class HelloRequest(SimpleRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data)
        if "rsaPubKey" in data:
            try:
                pubKey = RSA.importKey(data["rsaPubKey"])
                this.client.rsaKey = pubKey

                this.response = ErrorCode.OK
                this.response[1] = {"aesKey": base64.encodebytes(this.client.aesKey).decode("utf-8")}
            except ValueError as e:
                Logger.error(f"Failed to import client's RSA public key: {e}")
                this.response = ErrorCode.BAD_REQUEST
                this.response[1] = "Bad RSA public key"

        else:
            this.response = ErrorCode.BAD_REQUEST
            this.response[1] = "No RSA public key"

        this.client.encrypt = True
        this.respond()


class TimeZoneRequest(UserIdRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.DISCORD_ID)
        if this.response is None:
            this.response = ErrorCode.OK
            this.response[1] = Helpers.tzBot.db.getTimeZone(this.userId)
            if this.response[1] in {"", None}:
                this.response = ErrorCode.NOT_FOUND

        this.respond()


class AliasFromUserRequest(UserIdRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.DISCORD_ID, ApiPermissions.TZBOT_ALIAS)
        if this.response is None:
            this.response = ErrorCode.OK
            this.response[1] = Helpers.tzBot.db.getAlias(this.userId)
            if this.response[1] in {"", None}:
                this.response = ErrorCode.NOT_FOUND

        this.respond()


class UserFromAliasRequest(AliasRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.DISCORD_ID, ApiPermissions.TZBOT_ALIAS)
        if this.response is None:
            this.response = ErrorCode.OK
            this.response[1] = Helpers.tzBot.db.getUserByAlias(this.alias)
            if this.response[1] in {"", None}:
                this.response = ErrorCode.NOT_FOUND

        this.respond()


class TimeZoneFromAliasRequest(AliasRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.TZBOT_ALIAS)
        if this.response is None:
            this.response = ErrorCode.OK
            this.response[1] = Helpers.tzBot.db.getTimeZoneByAlias(this.alias)
            if this.response[1] in {"", None}:
                this.response = ErrorCode.NOT_FOUND

        this.respond()


class TimeZoneFromIPRequest(APIRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.IP_ADDRESS)

        askedIp = str(this.data.get("ip"))
        this.data["ip"] = "<redacted>"

        if this.response is None:
            if askedIp in [None, ""]:
                this.response = ErrorCode.BAD_REQUEST
            else:
                try:
                    requestCity = Helpers.tzBot.maxMindDb.city(askedIp)
                    if requestCity is None:
                        this.response = ErrorCode.NOT_FOUND
                    else:
                        this.response = ErrorCode.OK
                        this.response[1] = requestCity.location.time_zone
                        if not this.response[1]:
                            this.response = ErrorCode.NOT_FOUND

                except geoip2.errors.AddressNotFoundError as e:
                    Logger.error(f"Error getting timezone from IP {askedIp}: {e!s}")
                    this.response = ErrorCode.BAD_REQUEST

        this.respond()


class PingRequest(SimpleRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data)
        if this.response is None:
            this.response = ErrorCode.OK
            this.response[1] = "Pong"

        this.respond()


class CommandRequest(APIRequest):
    command: str | None = None
    args: list[str] | None = None

    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.COMMAND_API)

        if this.response is None:
            this.command = str(data.get("command"))
            this.args = data.get("args")

            if this.command is None:
                this.response = ErrorCode.BAD_REQUEST
            else:
                this.response = ErrorCode.OK
                Shell.parseAndExec(this.command + " " + " ".join(this.args))

        this.respond()


class TimeZoneOverridesPost(APIRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.TZ_OVERRIDES_POST)
        if this.response is None:
            errorMsgs: list[str] = []
            for uuid, timezone in data.items():
                if not Helpers.isUUID(uuid):
                    errorMsgs.append(f"Invalid UUID: {uuid}")

                if timezone not in checkList:
                    if this.response is None:
                        errorMsgs.append(f"Invalid timezone: {timezone}")
                    else:
                        errorMsgs.append(f"Invalid timezone: {timezone}")

            if errorMsgs:
                this.response = ErrorCode.BAD_REQUEST
                this.response[1] = ", ".join(errorMsgs)
                this.respond()
                return

            for uuid, timezone in data.items():
                Helpers.tzBot.db.addTzOverride(uuid, timezone)

            this.response = ErrorCode.OK
        this.respond()


class TimeZoneOverridesGet(APIRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.TZ_OVERRIDES_GET)
        if this.response is None:
            this.response = ErrorCode.OK
            this.response[1] = Helpers.tzBot.db.getTzOverrides()

        this.respond()


class TimeZoneOverrideRemove(UUIDRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.TZ_OVERRIDES_POST)
        if this.response is None:
            if Helpers.tzBot.db.getTzOverrideByUUID(this.uuid) in {None, ""}:
                this.response = ErrorCode.NOT_FOUND
                this.respond()
                return

            if Helpers.tzBot.db.removeTzOverride(this.uuid):
                this.response = ErrorCode.OK
            else:
                this.response = ErrorCode.INTERNAL_SERVER_ERROR

        this.respond()


class UserIdUUIDLinkPost(UUIDRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.UUID_POST)
        if this.response is None:
            this.timezone = this.data.get("timezone", None)
            if this.timezone not in Timezones.checkList:
                this.response = ErrorCode.NOT_FOUND
                this.respond()
                return

            if Helpers.tzBot.db.getUserIdByUUID(this.uuid) not in {None, ""} or this.uuid in Helpers.tzBot.linkCodes:
                this.response = ErrorCode.NOT_FOUND
                this.response[1] = "UUID already registered"
                this.respond()
                return

            this.code = Helpers.generateCharSequence(6)
            this.response = ErrorCode.OK
            this.response[1] = this.code

        this.respond()


class TimezoneFromUUIDRequest(UUIDRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.MINECRAFT_UUID)
        if this.response is None:
            timezone = Helpers.tzBot.db.getTimezoneByUUID(this.uuid)
            if timezone in {None, ""}:
                this.response = ErrorCode.NOT_FOUND
                this.respond()
                return

            this.response = ErrorCode.OK
            this.response[1] = timezone

        this.respond()


class ImageRequest(APIRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.IMAGE_API)
        if this.response is None:
            this.r: str = data.get("r", "0")
            this.g: str = data.get("g", "0")
            this.b: str = data.get("b", "0")

            if not Path("BMPGen").is_file():
                this.response = ErrorCode.INTERNAL_SERVER_ERROR
                this.response[1] = "Unsupported feature"
                this.respond()
                return

            try:
                subprocess.run(["./BMPGen", "-r", f"{this.r}", "-g", f"{this.g}", "-b", f"{this.b}"], check=True)  # noqa: S603
            except subprocess.CalledProcessError:
                this.response = ErrorCode.BAD_REQUEST
                this.response[1] = "There is a problem with your expression"
                this.respond()
                return

            subprocess.run(
                ["/usr/bin/magick", "output.bmp", "-define", "png:compression-level=9", "-define",
                 "png:compression-strategy=1", "output.png"], check=False
            )
            with open("output.png", "rb") as f:
                this.response = ErrorCode.OK
                this.response[1] = base64.b64encode(f.read()).decode()
                Path.unlink(Path("output.bmp"), missing_ok=True)
                Path.unlink(Path("output.png"), missing_ok=True)

        this.respond()
