#!/usr/bin/env python3
import asyncio
import os
import shutil
import subprocess
import time
from pathlib import Path

import aiofiles
import discord
import requests

from config.Config import Config, MaxmindConfig
from modules.TZBot import TZBot
from server.SocketServer import SocketServer
from shell.Logger import Logger
from shell.Shell import Shell


def getGeoIP(conf: MaxmindConfig) -> None:
    day = 86400
    dbStats = Path.stat(Path("GeoLite2-City.mmdb")) if Path("GeoLite2-City.mmdb").is_file() else None
    if dbStats is not None:
        currentTime = time.time()
        secondsDiff = currentTime - dbStats.st_ctime
        if secondsDiff < day:
            Logger.log("Skipping GeoLite2 database download, it was updated less than 24 hours ago.")
            return

    Logger.log("Downloading GeoLite2 database...")
    response = requests.get(
        "https://download.maxmind.com/geoip/databases/GeoLite2-City/download?suffix=tar.gz",
        auth=(str(conf.accountId), conf.token),
        stream=True,
        timeout=3,
    )

    with open("GeoLite2-City.tar.gz", "wb") as file:
        file.write(response.content)

    Path.mkdir(Path("GeoLite2-City"))
    subprocess.run(["/usr/bin/tar", "-xf", "GeoLite2-City.tar.gz", "-C", "GeoLite2-City"], check=False)
    shutil.move(f"GeoLite2-City/{os.listdir('GeoLite2-City')[0]}/GeoLite2-City.mmdb", "GeoLite2-City.mmdb")  # noqa: PTH208
    Path.unlink(Path("GeoLite2-City.tar.gz"))
    Path.unlink(Path("GeoLite2-City/"))


async def main() -> None:
    async with aiofiles.open("config.json") as f:
        config: Config = Config.schema().loads(await f.read())

    shell = Shell()
    shellTask = asyncio.create_task(shell.run_async())

    getGeoIP(config.maxmind)
    serverStarter = asyncio.create_task(SocketServer(config.server).start())

    client = TZBot(config, command_prefix="tz!", help_command=None, intents=discord.Intents.all())
    async with client:
        await client.start(config.token)

    tasks = await asyncio.gather(serverStarter, shellTask, return_exceptions=True)
    for result in tasks:
        if isinstance(result, Exception):
            Logger.log(f"Task failed: {result}")


asyncio.run(main())
