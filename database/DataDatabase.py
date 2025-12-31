import asyncio
from pathlib import Path
from typing import Final
from shared.Helpers import Helpers

import aiomysql
import aiosqlite

from config.Config import MariaDBConfig
from shell.Logger import Logger


class Database:
    DB_FILENAME: Final[Path] = Path("dbFiles/timezones.sqlite")

    def __init__(this, mdbConfig: MariaDBConfig) -> None:
        this.mdbConfig = mdbConfig

        asyncio.create_task(this._postInit())

    async def _postInit(this) -> None:
        this.conn = await aiosqlite.connect(this.DB_FILENAME)

        this.mdbPool = await aiomysql.create_pool(
            loop=asyncio.get_event_loop(),
            host=this.mdbConfig.host,
            user=this.mdbConfig.user,
            password=this.mdbConfig.password,
            db=this.mdbConfig.database,
            port=this.mdbConfig.port,
            autocommit=True,
        )

    async def executeSetQuery(this, query: str, mdbQuery: str, values: tuple) -> bool:
        cursor = await this.conn.execute(query, values)
        await this.conn.commit()

        async with this.mdbPool.acquire() as conn, conn.cursor() as cur:
            await cur.execute(mdbQuery, values)

            return cursor.rowcount != 0 and cur.rowcount != 0

    async def executeGetStrQuery(this, query: str, values: tuple) -> str | None:
        cursor = await this.conn.execute(query, values)
        await this.conn.commit()
        return (await cursor.fetchone())[0]

    async def setTimezone(this, userId: int, timezone: str, alias: str) -> bool:
        query: str = "INSERT INTO timezones (user, timezone) VALUES (?, ?)\
                 ON CONFLICT DO UPDATE SET timezone = ?, alias = ?;"
        mdbQuery: str = "INSERT INTO timezones (user, timezone) VALUES (%s, %s)\
                 ON DUPLICATE KEY UPDATE timezone = %s, alias = %s;"

        return await this.executeSetQuery(query, mdbQuery, (userId, timezone.replace(" ", "_"), alias, timezone.replace(" ", "_"), alias))

    async def getTimeZone(this, userId: int) -> str | None:
        query: str = "SELECT timezone from timezones WHERE user = ?"
        return await this.executeGetStrQuery(query, (userId,))

    async def assignUUIDToUserId(this, uuid: Helpers.UUIDStr, userId: int, timezone: str) -> bool:
        query: str = "INSERT INTO timezones (user, uuid, timezone, alias) VALUES (?, ?, ?, ?) ON CONFLICT(user) DO UPDATE SET uuid = ?;"
        mdbQuery: str = "INSERT INTO timezones (user, uuid, timezone, alias) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE uuid = %s;"

        return await this.executeSetQuery(query, mdbQuery, (userId, uuid, timezone.replace(" ", "_"), uuid, uuid))

    async def unassignUUIDFromUserId(this, userId: int) -> bool:
        query: str = "UPDATE timezones SET uuid = NULL WHERE user = ?"
        return await this.executeSetQuery(query, query.replace("?", "%s"), (userId,))

    async def getUUIDByUserId(this, userId: int) -> str | None:
        query: str = "SELECT uuid from timezones WHERE user = ?"
        return await this.executeGetStrQuery(query, (userId,))

    async def getUserIdByUUID(this, uuid: Helpers.UUIDStr) -> str | None:
        query: str = "SELECT user from timezones WHERE uuid = ?"
        return await this.executeGetStrQuery(query, (uuid,))

    async def getTimezoneByUUID(this, uuid: Helpers.UUIDStr) -> str | None:
        query: str = "SELECT timezone from timezones WHERE uuid = ?"
        return await this.executeGetStrQuery(query, (uuid,))
