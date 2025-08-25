#!/usr/bin/env python3
import asyncio
import shutil
import time
from pathlib import Path

import aiofiles
import aiohttp
import discord

from config.Config import Config, MaxmindConfig
from modules.TZBot import TZBot
from server.SocketServer import SocketServer
from shell.Logger import Logger
from shell.Shell import Shell


async def getGeoIP(conf: MaxmindConfig) -> None:
    day = 86400
    mmdbPath = Path("GeoLite2-City.mmdb")

    if mmdbPath.is_file():
        current_time = time.time()
        seconds_diff = current_time - mmdbPath.stat().st_ctime
        if seconds_diff < day:
            Logger.log("Skipping GeoLite2 database download, it was updated less than 24 hours ago.")
            return

    Logger.log("Downloading GeoLite2 database...")

    url = "https://download.maxmind.com/geoip/databases/GeoLite2-City/download?suffix=tar.gz"

    async with aiohttp.ClientSession() as session, session.get(url, timeout=aiohttp.ClientTimeout(total=10), auth=aiohttp.BasicAuth(str(conf.accountId), conf.token, 'utf-8')) as response:
        if response.status != 200:  # noqa: PLR2004
            Logger.error(f"Failed to download GeoLite2 database: HTTP {response.status}")
            return

        async with aiofiles.open("GeoLite2-City.tar.gz", "wb") as file:
            content = await response.read()
            await file.write(content)

    Path("GeoLite2-City").mkdir(exist_ok=True)

    proc = await asyncio.create_subprocess_exec(
        "/usr/bin/tar", "-xf", "GeoLite2-City.tar.gz", "-C", "GeoLite2-City", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    await proc.communicate()

    extractedDir = Path("GeoLite2-City")
    subdirs = [d for d in extractedDir.iterdir() if d.is_dir()]
    if subdirs:
        mmdbSource = subdirs[0] / "GeoLite2-City.mmdb"
        if mmdbSource.exists():
            shutil.move(str(mmdbSource), "GeoLite2-City.mmdb")

    Path("GeoLite2-City.tar.gz").unlink(missing_ok=True)
    shutil.rmtree("GeoLite2-City", ignore_errors=True)


async def main() -> None:
    async with aiofiles.open("config.json") as f:
        config: Config = Config.schema().loads(await f.read())

    shellTask = asyncio.create_task(Shell().run_async())
    await getGeoIP(config.maxmind)

    serverStarter = asyncio.create_task(SocketServer(config.server).start())

    client = TZBot(config, command_prefix="tz!", help_command=None, intents=discord.Intents.all())
    botTask = asyncio.create_task(client.start(config.token))

    tasks = [serverStarter, shellTask, botTask]
    try:
        await asyncio.gather(*tasks)
    except Exception as e:  # noqa: BLE001
        Logger.error(f"Unhandled exception: {e}")


asyncio.run(main())
