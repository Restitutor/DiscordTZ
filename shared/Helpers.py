import asyncio
import json
import random
import re
import string
from pathlib import Path

import aiofiles

from shell.Logger import Logger


async def getHosts() -> dict[str, str]:
    pattern = re.compile(r"\b((?:10|192\.168|172\.(?:1[6-9]|2[0-9]|3[0-1]))(?:\.\d{1,3}){3})\s+(\S+)", re.IGNORECASE)

    try:
        async with aiofiles.open("/etc/hosts") as f:
            content = await f.read()
    except FileNotFoundError:
        Logger.error("Hosts file not found.")
        return {}
    except PermissionError:
        Logger.error("Permission denied when trying to read /etc/hosts.")
        return {}

    return dict(pattern.findall(content))


async def isLocalSubnet(ip: str) -> bool:
    ipRegex = re.compile(
        r"""
                ^(?:
                    # Private ranges
                    10(?:\.\d{1,3}){3} |                            # 10.0.0.0/8
                    172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2} |    # 172.16.0.0 - 172.31.255.255
                    192\.168(?:\.\d{1,3}){2} |                     # 192.168.0.0/16

                    # Loopback
                    127(?:\.\d{1,3}){3} |                          # 127.0.0.0/8

                    # Link-local
                    169\.254(?:\.\d{1,3}){2} |                     # 169.254.0.0/16

                    # Carrier-grade NAT
                    100\.(?:6[4-9]|[7-9]\d|1[0-1]\d|12[0-7])(?:\.\d{1,3}){2} |  # 100.64.0.0/10

                    # Reserved for documentation
                    192\.0\.2\.\d{1,3} |                       # 192.0.2.0/24
                    198\.51\.100\.\d{1,3} |                    # 198.51.100.0/24
                    203\.0\.113\.\d{1,3} |                     # 203.0.113.0/24

                    # Reserved for future use
                    240(?:\.\d{1,3}){3} |                          # 240.0.0.0/4
                    255\.255\.255\.255 |                           # Broadcast

                    # IETF Protocol Assignments
                    192\.0\.0\.\d{1,3} |                       # 192.0.0.0/24

                    # Benchmarking
                    198\.18(?:\.\d{1,3}){2} |                      # 198.18.0.0/15
                    198\.19(?:\.\d{1,3}){2}
                )$
                """,
        re.VERBOSE,
    )
    return bool(ipRegex.match(ip))


async def isUUID(uniqueId: str) -> bool:
    pattern = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$")
    return bool(pattern.match(uniqueId))


async def generateCharSequence(n: int) -> str:
    return "".join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(n))


async def parseJson(data: str) -> dict | None:
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError):
        return None


async def generateImage(r: str, g: str, b: str) -> bool:
    if not Path("BMPGen").is_file():
        Logger.error("BMPGen is not present!")
        return False

    bmpGen = await asyncio.create_subprocess_exec(
        "./BMPGen", "-r", f"{r}", "-g", f"{g}", "-b", f"{b}", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await bmpGen.communicate()

    if bmpGen.returncode != 0:
        Logger.error(f"There was an error generating BMP image. Return code: {bmpGen.returncode}; stderr: {stderr.decode('utf-8', errors='ignore')}")
        Logger.error(f"Red: {r}")
        Logger.error(f"Green: {g}")
        Logger.error(f"Blue: {b}")
        return False

    magick = await asyncio.create_subprocess_exec(
        "/usr/bin/magick",
        "output.bmp",
        "-define",
        "png:compression-level=9",
        "-define",
        "png:compression-strategy=1",
        "output.png",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await magick.communicate()

    if magick.returncode != 0:
        Logger.error(
            f"There was an error with conversion from BMP to PNG. Return code: {magick.returncode}; stderr: {stderr.decode('utf-8', errors='ignore')}"
        )
        return False

    Path.unlink(Path("output.bmp"), missing_ok=True)
    return True


tzBot = None
