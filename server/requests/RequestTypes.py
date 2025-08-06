from enum import Enum

from server.requests.Requests import (
    AliasFromUserRequest,
    CommandRequest,
    HelloRequest,
    PingRequest,
    TimeZoneFromAliasRequest,
    TimeZoneFromIPRequest,
    TimezoneFromUUIDRequest,
    TimeZoneOverrideRemove,
    TimeZoneOverridesGet,
    TimeZoneOverridesPost,
    TimeZoneRequest,
    UserFromAliasRequest,
    UserIdUUIDLinkPost,
)


class RequestType(Enum):
    HELLO = HelloRequest
    TIMEZONE_FROM_USERID = TimeZoneRequest
    ALIAS_FROM_USERID = AliasFromUserRequest
    USERID_FROM_ALIAS = UserFromAliasRequest
    TIMEZONE_FROM_ALIAS = TimeZoneFromAliasRequest
    TIMEZONE_FROM_IP = TimeZoneFromIPRequest
    PING = PingRequest
    COMMAND = CommandRequest
    TIMEZONE_OVERRIDES_POST = TimeZoneOverridesPost
    TIMEZONE_OVERRIDES_GET = TimeZoneOverridesGet
    USER_ID_UUID_LINK_POST = UserIdUUIDLinkPost
    TIMEZONE_FROM_UUID = TimezoneFromUUIDRequest
    TIMEZONE_OVERRIDE_REMOVE = TimeZoneOverrideRemove

    def __call__(this, *args, **kwargs):
        return this.value(*args, **kwargs)

    @classmethod
    def get(cls, value, default=None):
        for member in cls:
            if member.value == value or member.value.__name__ == value:
                return member
        return default
