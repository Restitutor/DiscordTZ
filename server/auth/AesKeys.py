import contextlib
import os

aesKeysByIp: dict[str, bytes] = {}


def getAesKeyByIp(ip: str) -> bytes:
    if (ip not in aesKeysByIp):
        aesKeysByIp[ip] = os.urandom(32)

    return aesKeysByIp[ip]


def regenAesKeysByIp(ip: str) -> bytes:
    with contextlib.suppress(KeyError):
        aesKeysByIp.pop(ip)

    return getAesKeyByIp(ip)
