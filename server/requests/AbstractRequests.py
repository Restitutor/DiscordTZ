import json
import random

import geoip2
from geoip2 import errors  # noqa: F401
from geoip2.models import City

from server.Api import ApiKey, ApiPermissions
from server.EventHandler import EventHandler
from server.protocol.Client import Client
from server.protocol.TCP import TCPClient
from server.ServerError import ErrorCode
from shared import Helpers
from shell.Logger import Logger


class SimpleRequest:
    client: Client
    headers: dict
    data: dict
    response: list | None = None
    city: City | None
    protocol: str

    commonEventHandler: EventHandler = EventHandler()

    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        this.client = client
        this.data = data
        this.headers = headers

        this.protocol = "TCP" if isinstance(client, TCPClient) else "UDP"
        try:
            this.city = Helpers.tzBot.maxMindDb.city(this.client.ipAddress[0])
        except geoip2.errors.AddressNotFoundError:
            this.city = None

        if this.__class__.__name__ == "SimpleRequest":
            this.client.encrypt = False

    async def process(this) -> None:
        await this.respond()

    async def respond(this) -> None:
        if this.__class__.__name__ == "SimpleRequest":
            this.response = ErrorCode.BAD_REQUEST
            this.client.encrypt = False

        await sendResponse(this)

    def __str__(this) -> str:
        return f"{this.__class__.__name__}({this.protocol}, {this.client.ipAddress}, {this.headers}, {this.data})"


class PartiallyEncryptedRequest(SimpleRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data)

    async def process(this) -> None:
        if not (this.client.encrypt and await Helpers.isLocalSubnet(this.client.ipAddress[0])):
            this.response = ErrorCode.BAD_REQUEST
            this.response[1] = "Bad Request, Unencrypted"


class EncryptedRequest(PartiallyEncryptedRequest):
    def __init__(this, client: Client, headers: dict, data: dict) -> None:
        super().__init__(client, headers, data)

    async def process(this) -> None:
        if not (this.response and this.client.encrypt):
            this.response = ErrorCode.BAD_REQUEST
            this.response[1] = "Bad Request, Unencrypted"


class APIRequest(PartiallyEncryptedRequest):
    def __init__(this, client: Client, headers: dict, data: dict, *requiredPerms: ApiPermissions) -> None:
        super().__init__(client, headers, data)
        this.requiredPerms = requiredPerms
        this.rawApiKey = this.headers.get("apiKey")

    async def process(this) -> None:
        if not this.response:
            if not this.rawApiKey:
                this.response = ErrorCode.FORBIDDEN
                return

            if not await Helpers.tzBot.apiDb.isValidKey(this.rawApiKey):
                Logger.error("Key isn't in the DB")
                this.response = ErrorCode.FORBIDDEN
                return

            apiKey = ApiKey.fromDbForm(this.rawApiKey)

            if not apiKey.hasPermissions(*this.requiredPerms):
                Logger.error("No permissions")
                this.response = ErrorCode.FORBIDDEN
                return


class UserIdRequest(APIRequest):
    def __init__(this, client: Client, headers: dict, data: dict, *requiredPerms: ApiPermissions) -> None:
        super().__init__(client, headers, data, *requiredPerms)
        this.userId = int(data.get("userId")) if str(data.get("userId")).isnumeric() else None

    async def process(this) -> None:
        if not (this.response and this.userId):
            this.response = ErrorCode.BAD_REQUEST


class AliasRequest(APIRequest):
    def __init__(this, client: Client, headers: dict, data: dict, *requiredPerms: ApiPermissions) -> None:
        super().__init__(client, headers, data, *requiredPerms)
        this.alias = str(data.get("alias"))

    async def process(this) -> None:
        if not this.response and this.alias is None:
            this.response = ErrorCode.BAD_REQUEST


class UUIDRequest(APIRequest):
    def __init__(this, client: Client, headers: dict, data: dict, *requiredPerms: ApiPermissions) -> None:
        super().__init__(client, headers, data, *requiredPerms)
        this.uuid = data.get("uuid")

    async def process(this) -> None:
        if (not this.response and this.uuid is None) or not await Helpers.isUUID(this.uuid):
            this.response = ErrorCode.BAD_REQUEST
            this.response[1] = "Invalid UUID"


async def chinaResponse(request: SimpleRequest) -> None:
    messages: list[str] = [
        "Taiwan is a country.",
        "Fuck Xi Jinping.",
        "Fuck the CCP.",
        "Free Taiwan.",
        "Tiananmen Square June 4th 1989.",
        "Xi Jinping = Winnie the Pooh",
        "动态网自由门",
        "天安門",
        "天安门",
        "法輪功",
        "李 洪 志",
        "Free Tibet",
        "六四天安門事件",
        "The Tiananmen Square protests of 1989",
        "天安門 大屠殺",
        "The Tiananmen Square Massacre",
        "反右派鬥爭",
        "The Anti-Rightist Struggle",
        "大躍進政策",
        "The Great Leap Forward",
        "文化大革命",
        "The Bad Proletarian Cultural Revolution",
        "人權",
        "Human Rights",
        "民運",
        "Democratization",
        "自由",
        "Freedom",
        "獨立",
        "Independence",
        "多黨制",
        "Multi-party system",
        "台灣",
        "臺灣",
        "Taiwan",
        "Formosa",
        "西藏",
        "新疆維吾爾自治區",
        "民主",
        "言論",
        "思想",
    ]

    request.response[0] = 403
    request.response[1] = random.choice(messages)  # noqa: S311
    request.client.encrypt = False


async def sendResponse(request: SimpleRequest) -> None:
    if request.city is not None and request.city.country.iso_code in {"SG", "CN", "MO", "HK"}:
        await chinaResponse(request)
    elif request.response[0] == ErrorCode.OK[0]:
        request.commonEventHandler.triggerSuccess(request)
    else:
        request.commonEventHandler.triggerError(request)

    resp = {"code": request.response[0], "message": request.response[1]}

    Logger.log(f"Responding with: {resp}")
    request.client.send(json.dumps(resp).encode())
