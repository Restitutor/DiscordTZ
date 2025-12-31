from enum import Enum

from server.requests.AbstractRequests import SimpleRequest
from server.requests.Requests import (
    IsLinkedRequest,
    PingRequest,
    TimeZoneFromIPRequest,
    TimezoneFromUUIDRequest,
    TimeZoneRequest,
    UserIDFromUUIDRequest,
    UserIdUUIDLinkPost,
    UUIDFromUserIDRequest
)


class RequestType(Enum):
    TIMEZONE_FROM_USERID = TimeZoneRequest
    TIMEZONE_FROM_IP = TimeZoneFromIPRequest
    PING = PingRequest
    USER_ID_UUID_LINK_POST = UserIdUUIDLinkPost
    TIMEZONE_FROM_UUID = TimezoneFromUUIDRequest
    IS_LINKED = IsLinkedRequest
    USER_ID_FROM_UUID = UserIDFromUUIDRequest
    UUID_FROM_USER_ID = UUIDFromUserIDRequest

    def __call__(this, *args, **kwargs) -> SimpleRequest:
        return this.value(*args, **kwargs)
