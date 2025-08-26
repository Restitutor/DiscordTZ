import asyncio
import base64
import subprocess
from pathlib import Path

import aiofiles
import geoip2.errors
from Crypto.PublicKey import RSA

from server.Api import ApiPermissions
from server.protocol.Client import Client
from server.requests.AbstractRequests import AliasRequest, APIRequest, SimpleRequest, UserIdRequest, UUIDRequest
from server.ServerError import ErrorCode
from shared import Helpers, Timezones
from shared.Timezones import checkList
from shell.Logger import Logger


class HelloRequest(SimpleRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data)
        this.rsaPubKey: str | None = data.get("rsaPubKey")

    async def process(this) -> None:
        await super().process()

        if not this.response:
            if this.rsaPubKey:
                try:
                    pubKey = RSA.importKey(this.rsaPubKey)
                    this.client.rsaKey = pubKey

                    this.response = ErrorCode.OK
                    this.response.message = {"aesKey": base64.encodebytes(this.client.aesKey).decode("utf-8")}
                except ValueError as e:
                    Logger.error(f"Failed to import client's RSA public key: {e}")
                    this.response = ErrorCode.BAD_REQUEST
                    this.response.message = "Bad RSA public key"

            else:
                this.response = ErrorCode.BAD_REQUEST
                this.response.message = "No RSA public key"

            this.client.encrypt = True
        await this.respond()


class TimeZoneRequest(UserIdRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.DISCORD_ID)

    async def process(this) -> None:
        await super().process()

        if not this.response:
            this.response = ErrorCode.OK
            this.response.message = await Helpers.tzBot.db.getTimeZone(this.userId)
            if not this.response.message:
                this.response = ErrorCode.NOT_FOUND

        await this.respond()


class AliasFromUserRequest(UserIdRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.DISCORD_ID, ApiPermissions.TZBOT_ALIAS)

    async def process(this) -> None:
        await super().process()

        if not this.response:
            this.response = ErrorCode.OK
            this.response.message = await Helpers.tzBot.db.getAlias(this.userId)
            if not this.response.message:
                this.response = ErrorCode.NOT_FOUND

        await this.respond()


class UserFromAliasRequest(AliasRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.DISCORD_ID, ApiPermissions.TZBOT_ALIAS)

    async def process(this) -> None:
        await super().process()

        if not this.response:
            this.response = ErrorCode.OK
            this.response.message = await Helpers.tzBot.db.getUserByAlias(this.alias)
            if not this.response.message:
                this.response = ErrorCode.NOT_FOUND

        await this.respond()


class TimeZoneFromAliasRequest(AliasRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.TZBOT_ALIAS)

    async def process(this) -> None:
        await super().process()

        if not this.response:
            this.response = ErrorCode.OK
            this.response.message = await Helpers.tzBot.db.getTimeZoneByAlias(this.alias)
            if not this.response.message:
                this.response = ErrorCode.NOT_FOUND

        await this.respond()


class TimeZoneFromIPRequest(APIRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.IP_ADDRESS)

        this.askedIp = str(this.data.get("ip"))
        this.data["ip"] = "<redacted>"

    async def process(this) -> None:
        await super().process()

        if not this.response:
            if not this.askedIp:
                this.response = ErrorCode.BAD_REQUEST
            else:
                try:
                    requestCity = Helpers.tzBot.maxMindDb.city(this.askedIp)
                    if not requestCity:
                        this.response = ErrorCode.NOT_FOUND
                    else:
                        this.response = ErrorCode.OK
                        this.response.message = requestCity.location.time_zone
                        if not this.response.message:
                            this.response = ErrorCode.NOT_FOUND

                except geoip2.errors.AddressNotFoundError as e:
                    Logger.error(f"Error getting timezone from IP {this.askedIp}: {e!s}")
                    this.response = ErrorCode.BAD_REQUEST

        await this.respond()


class PingRequest(SimpleRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data)

    async def process(this) -> None:
        await super().process()

        if not this.response:
            this.response = ErrorCode.OK
            this.response.message = "Pong"

        await this.respond()


class CommandRequest(APIRequest):
    command: str | None = None
    args: list[str] | None = None

    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.COMMAND_API)
        this.command = str(data.get("command"))
        this.args = data.get("args")

    async def process(this) -> None:
        await super().process()

        this.response = ErrorCode.INTERNAL_SERVER_ERROR
        this.response.message = "Not implemented."

        await this.respond()
        # if this.response is None:
        #     if this.command is None:
        #         this.response = ErrorCode.BAD_REQUEST
        #     else:
        #         this.response = ErrorCode.OK
        #         Shell.parseAndExec(this.command + " " + " ".join(this.args))

        # await this.respond()


class TimeZoneOverridesPost(APIRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.TZ_OVERRIDES_POST)

    async def process(this) -> None:
        await super().process()

        if not this.response:
            errorMsgs: list[str] = []
            for uuid, timezone in this.data.items():
                if not await Helpers.isUUID(uuid):
                    errorMsgs.append(f"Invalid UUID: {uuid}")

                if timezone not in checkList:
                    errorMsgs.append(f"Invalid timezone: {timezone}")

            if errorMsgs:
                this.response = ErrorCode.BAD_REQUEST
                this.response.message = ", ".join(errorMsgs)
                await this.respond()
                return

            for uuid, timezone in this.data.items():
                await Helpers.tzBot.db.addTzOverride(uuid, timezone)

            this.response = ErrorCode.OK

        await this.respond()


class TimeZoneOverridesGet(APIRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.TZ_OVERRIDES_GET)

    async def process(this) -> None:
        await super().process()

        if not this.response:
            this.response = ErrorCode.OK
            this.response.message = await Helpers.tzBot.db.getTzOverrides()

        await this.respond()


class TimeZoneOverrideRemove(UUIDRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.TZ_OVERRIDES_POST)

    async def process(this) -> None:
        await super().process()

        if not this.response:
            if await Helpers.tzBot.db.getTzOverrideByUUID(this.uuid) in {None, ""}:
                this.response = ErrorCode.NOT_FOUND
                await this.respond()
                return

            if await Helpers.tzBot.db.removeTzOverride(this.uuid):
                this.response = ErrorCode.OK
            else:
                this.response = ErrorCode.INTERNAL_SERVER_ERROR

        await this.respond()


class UserIdUUIDLinkPost(UUIDRequest):
    code: str = ""

    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.UUID_POST)
        this.timezone = this.data.get("timezone")

    async def process(this) -> None:
        await super().process()

        if not this.response:
            if this.timezone not in Timezones.checkList:
                this.response = ErrorCode.NOT_FOUND
                await this.respond()
                return

            if await Helpers.tzBot.db.getUserIdByUUID(this.uuid) or this.uuid in [val[0] for val in Helpers.tzBot.linkCodes.values()]:
                this.response = ErrorCode.CONFLICT
                this.response.message = "UUID already registered"
                await this.respond()
                return

            this.code = await Helpers.generateCharSequence(6)

            Helpers.tzBot.linkCodes.update({this.code: (this.uuid, this.timezone)})
            asyncio.create_task(Helpers.tzBot.removeCode(15, this.code))

            this.response = ErrorCode.OK
            this.response.message = this.code

        await this.respond()


class TimezoneFromUUIDRequest(UUIDRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.MINECRAFT_UUID)

    async def process(this) -> None:
        await super().process()

        if not this.response:
            timezone = await Helpers.tzBot.db.getTimezoneByUUID(this.uuid)
            if not timezone:
                this.response = ErrorCode.NOT_FOUND
                await this.respond()
                return

            this.response = ErrorCode.OK
            this.response.message = timezone

        await this.respond()


class ImageRequest(APIRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.IMAGE_API)
        if not this.response:
            this.r: str = data.get("r", "0")
            this.g: str = data.get("g", "0")
            this.b: str = data.get("b", "0")

    async def process(this) -> None:
        await super().process()

        if not Path("BMPGen").is_file():
            this.response = ErrorCode.INTERNAL_SERVER_ERROR
            this.response.message = "Unsupported feature"
            await this.respond()
            return

        try:
            subprocess.run(["./BMPGen", "-r", f"{this.r}", "-g", f"{this.g}", "-b", f"{this.b}"], check=True)  # noqa
        except subprocess.CalledProcessError:
            this.response = ErrorCode.BAD_REQUEST
            this.response.message = "There is a problem with your expression"
            await this.respond()
            return

        subprocess.run(  # noqa
            ["/usr/bin/magick", "output.bmp", "-define", "png:compression-level=9", "-define", "png:compression-strategy=1", "output.png"],
            check=False,
        )

        async with aiofiles.open("output.png", "rb") as f:
            this.response = ErrorCode.OK
            this.response.message = base64.b64encode(await f.read()).decode()
            Path.unlink(Path("output.bmp"), missing_ok=True)
            Path.unlink(Path("output.png"), missing_ok=True)

        await this.respond()


class IsLinkedRequest(UUIDRequest):
    def __init__(self, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.MINECRAFT_UUID)

    async def process(this) -> None:
        await super().process()

        if not this.response:
            if await Helpers.tzBot.db.getTimezoneByUUID(this.uuid):
                this.response = ErrorCode.OK
            else:
                this.response = ErrorCode.NOT_FOUND

        await this.respond()


class UserIDFromUUIDRequest(UUIDRequest):
    def __init__(self, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.MINECRAFT_UUID, ApiPermissions.DISCORD_ID)

    async def process(this) -> None:
        await super().process()

        if not this.response:
            if not (userId := await Helpers.tzBot.db.getUserIdByUUID(this.uuid)):
                this.response = ErrorCode.NOT_FOUND
            else:
                this.response = ErrorCode.OK
                this.response.message = userId

        await this.respond()
