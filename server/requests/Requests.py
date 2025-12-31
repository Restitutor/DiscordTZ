import asyncio
from typing import override

import geoip2.errors

from server.Api import ApiPermissions
from server.ServerError import ErrorCode
from server.protocol.Client import Client
from server.requests.AbstractRequests import APIRequest, SimpleRequest, UserIdRequest, UUIDRequest, \
    autoRespond
from shared.Helpers import Helpers
from shared.Timezones import Timezones
from shell.Logger import Logger


class TimeZoneRequest(UserIdRequest):
    def __init__(this, client: Client, headers: dict, data: dict, tzBot: "TZBot") -> None:
        super().__init__(client, headers, data, tzBot, ApiPermissions.DISCORD_ID)

    @override
    @autoRespond
    async def process(this) -> None:
        await super().process()

        if not this.response:
            this.response = ErrorCode.OK
            this.response.message = await Helpers.tzBot.db.getTimeZone(this.userId)
            if not this.response.message:
                this.response = ErrorCode.NOT_FOUND


class TimeZoneFromIPRequest(APIRequest):
    def __init__(this, client: Client, headers: dict, data: dict, tzBot: "TZBot") -> None:
        super().__init__(client, headers, data, tzBot, ApiPermissions.IP_ADDRESS)

        this.askedIp = str(this.data.get("ip"))
        this.data["ip"] = "<redacted>"

    @override
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
    def __init__(this, client: Client, headers: dict, data: dict, tzBot: "TZBot") -> None:
        super().__init__(client, headers, data, tzBot)

    @override
    @autoRespond
    async def process(this) -> None:
        if not this.response:
            this.response = ErrorCode.OK
            this.response.message = "Pong"


class UserIdUUIDLinkPost(UUIDRequest):
    code: str = ""

    def __init__(this, client: Client, headers: dict, data: dict, tzBot: "TZBot") -> None:
        super().__init__(client, headers, data, tzBot, ApiPermissions.UUID_POST)
        this.timezone = this.data.get("timezone")

    @override
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
    def __init__(this, client: Client, headers: dict, data: dict, tzBot: "TZBot") -> None:
        super().__init__(client, headers, data, tzBot, ApiPermissions.MINECRAFT_UUID)

    @override
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


class IsLinkedRequest(UUIDRequest):
    def __init__(self, client: Client, headers: dict, data: dict, tzBot: "TZBot") -> None:
        super().__init__(client, headers, data, tzBot, ApiPermissions.MINECRAFT_UUID)

    @override
    @autoRespond
    async def process(this) -> None:
        await super().process()

        if not this.response:
            if await Helpers.tzBot.db.getTimezoneByUUID(this.uuid):
                this.response = ErrorCode.OK
            else:
                this.response = ErrorCode.NOT_FOUND


class UserIDFromUUIDRequest(UUIDRequest):
    def __init__(self, client: Client, headers: dict, data: dict, tzBot: "TZBot") -> None:
        super().__init__(client, headers, data, tzBot, ApiPermissions.MINECRAFT_UUID, ApiPermissions.DISCORD_ID)

    @override
    @autoRespond
    async def process(this) -> None:
        await super().process()

        if not this.response:
            if not (userId := await Helpers.tzBot.db.getUserIdByUUID(this.uuid)):
                this.response = ErrorCode.NOT_FOUND
            else:
                this.response = ErrorCode.OK
                this.response.message = userId