import asyncio
import base64

import geoip2.errors
from Crypto.PublicKey import RSA

from server.Api import ApiPermissions
from server.ServerError import ErrorCode
from server.protocol.Client import Client
from server.requests.AbstractRequests import AliasRequest, APIRequest, SimpleRequest, UserIdRequest, UUIDRequest, \
    autoRespond
from shared.Timezones import Timezones
from shared.Helpers import Helpers
from shell.Logger import Logger


class HelloRequest(SimpleRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data)
        this.rsaPubKey: str | None = data.get("rsaPubKey")

    @autoRespond
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


class TimeZoneRequest(UserIdRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.DISCORD_ID)

    @autoRespond
    async def process(this) -> None:
        await super().process()

        if not this.response:
            this.response = ErrorCode.OK
            this.response.message = await Helpers.tzBot.db.getTimeZone(this.userId)
            if not this.response.message:
                this.response = ErrorCode.NOT_FOUND


class AliasFromUserRequest(UserIdRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.DISCORD_ID, ApiPermissions.TZBOT_ALIAS)

    @autoRespond
    async def process(this) -> None:
        await super().process()

        if not this.response:
            this.response = ErrorCode.OK
            this.response.message = await Helpers.tzBot.db.getAlias(this.userId)
            if not this.response.message:
                this.response = ErrorCode.NOT_FOUND


class UserFromAliasRequest(AliasRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.DISCORD_ID, ApiPermissions.TZBOT_ALIAS)

    @autoRespond
    async def process(this) -> None:
        await super().process()

        if not this.response:
            this.response = ErrorCode.OK
            this.response.message = await Helpers.tzBot.db.getUserByAlias(this.alias)
            if not this.response.message:
                this.response = ErrorCode.NOT_FOUND


class TimeZoneFromAliasRequest(AliasRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.TZBOT_ALIAS)

    @autoRespond
    async def process(this) -> None:
        await super().process()

        if not this.response:
            this.response = ErrorCode.OK
            this.response.message = await Helpers.tzBot.db.getTimeZoneByAlias(this.alias)
            if not this.response.message:
                this.response = ErrorCode.NOT_FOUND


class TimeZoneFromIPRequest(APIRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.IP_ADDRESS)

        this.askedIp = str(this.data.get("ip"))
        this.data["ip"] = "<redacted>"

    @autoRespond
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


class PingRequest(SimpleRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data)

    @autoRespond
    async def process(this) -> None:
        await super().process()

        if not this.response:
            this.response = ErrorCode.OK
            this.response.message = "Pong"


class CommandRequest(APIRequest):
    command: str | None = None
    args: list[str] | None = None

    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.COMMAND_API)
        this.command = str(data.get("command"))
        this.args = data.get("args")

    @autoRespond
    async def process(this) -> None:
        await super().process()

        this.response = ErrorCode.INTERNAL_SERVER_ERROR
        this.response.message = "Not implemented."


class TimeZoneOverridesPost(APIRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.TZ_OVERRIDES_POST)

    @autoRespond
    async def process(this) -> None:
        await super().process()

        if not this.response:
            errorMsgs: set[str] = set()
            for uuid, timezone in this.data.items():
                if not await Helpers.isUUID(uuid):
                    errorMsgs.add(f"Invalid UUID: {uuid}")

                if timezone not in Timezones.CHECK_LIST:
                    errorMsgs.add(f"Invalid timezone: {timezone}")

            if errorMsgs:
                this.response = ErrorCode.BAD_REQUEST
                this.response.message = "; ".join(errorMsgs)

            else:
                for uuid, timezone in this.data.items():
                    await Helpers.tzBot.db.addTzOverride(uuid, timezone)

                this.response = ErrorCode.OK


class TimeZoneOverridesGet(APIRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.TZ_OVERRIDES_GET)

    @autoRespond
    async def process(this) -> None:
        await super().process()

        if not this.response:
            this.response = ErrorCode.OK
            this.response.message = await Helpers.tzBot.db.getTzOverrides()


class TimeZoneOverrideRemove(UUIDRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.TZ_OVERRIDES_POST)

    @autoRespond
    async def process(this) -> None:
        await super().process()

        if not this.response:
            if await Helpers.tzBot.db.getTzOverrideByUUID(this.uuid) in {None, ""}:
                this.response = ErrorCode.NOT_FOUND

            elif await Helpers.tzBot.db.removeTzOverride(this.uuid):
                this.response = ErrorCode.OK
            else:
                this.response = ErrorCode.INTERNAL_SERVER_ERROR


class UserIdUUIDLinkPost(UUIDRequest):
    code: str = ""

    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.UUID_POST)
        this.timezone = this.data.get("timezone")

    @autoRespond
    async def process(this) -> None:
        await super().process()

        if not this.response:
            if this.timezone not in Timezones.CHECK_LIST:
                this.response = ErrorCode.NOT_FOUND

            elif await Helpers.tzBot.db.getUserIdByUUID(this.uuid) or this.uuid in [val[0] for val in Helpers.tzBot.linkCodes.values()]:
                this.response = ErrorCode.CONFLICT
                this.response.message = "UUID already registered"

            else:
                this.code = await Helpers.generateCharSequence(6)

                Helpers.tzBot.linkCodes.update({this.code: (this.uuid, this.timezone)})
                asyncio.create_task(Helpers.tzBot.removeCode(15, this.code))

                this.response = ErrorCode.OK
                this.response.message = this.code


class TimezoneFromUUIDRequest(UUIDRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.MINECRAFT_UUID)

    @autoRespond
    async def process(this) -> None:
        await super().process()

        if not this.response:
            timezone = await Helpers.tzBot.db.getTimezoneByUUID(this.uuid)
            if not timezone:
                this.response = ErrorCode.NOT_FOUND

            else:
                this.response = ErrorCode.OK
                this.response.message = timezone


class ImageRequest(APIRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.IMAGE_API)
        if not this.response:
            this.r: str = data.get("r", "0")
            this.g: str = data.get("g", "0")
            this.b: str = data.get("b", "0")

    @autoRespond
    async def process(this) -> None:
        await super().process()
        if not this.response:
            this.response = ErrorCode.INTERNAL_SERVER_ERROR
            this.response.message = "Not implemented."


class IsLinkedRequest(UUIDRequest):
    def __init__(self, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.MINECRAFT_UUID)

    @autoRespond
    async def process(this) -> None:
        await super().process()

        if not this.response:
            if await Helpers.tzBot.db.getTimezoneByUUID(this.uuid):
                this.response = ErrorCode.OK
            else:
                this.response = ErrorCode.NOT_FOUND


class UserIDFromUUIDRequest(UUIDRequest):
    def __init__(self, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data, ApiPermissions.MINECRAFT_UUID, ApiPermissions.DISCORD_ID)

    @autoRespond
    async def process(this) -> None:
        await super().process()

        if not this.response:
            if not (userId := await Helpers.tzBot.db.getUserIdByUUID(this.uuid)):
                this.response = ErrorCode.NOT_FOUND
            else:
                this.response = ErrorCode.OK
                this.response.message = userId