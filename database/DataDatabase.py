import asyncio

import aiomysql
import aiosqlite

from config.Config import MariaDBConfig
from shell.Logger import Logger


class Database:
    def __init__(this, filename: str, mdbConfig: MariaDBConfig) -> None:
        this.filename = filename
        this.mdbConfig = mdbConfig

        asyncio.create_task(this._postInit())

    async def _postInit(this) -> None:
        this.conn = await aiosqlite.connect(this.filename)

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
        if not (val := await cursor.fetchone()):
            return None

        return str(val[0])

    async def setTimezone(this, userId: int, timezone: str, alias: str) -> bool:
        query: str = "INSERT INTO timezones (user, timezone, alias) VALUES (?, ?, ?)\
                 ON CONFLICT DO UPDATE SET timezone = ?, alias = ?;"
        mdbQuery: str = "INSERT INTO timezones (user, timezone, alias) VALUES (%s, %s, %s)\
                 ON DUPLICATE KEY UPDATE timezone = %s, alias = %s;"

        return await this.executeSetQuery(query, mdbQuery, (userId, timezone.replace(" ", "_"), alias, timezone.replace(" ", "_"), alias))

    async def setAlias(this, userId: int, alias: str) -> bool:
        query: str = "UPDATE timezones SET alias = ? WHERE user = ?;"
        return await this.executeSetQuery(query, query.replace("?", "%s"), (alias, userId))

    async def getTimeZone(this, userId: int) -> str | None:
        query: str = "SELECT timezone from timezones WHERE user = ?"
        return await this.executeGetStrQuery(query, (userId,))

    async def getAlias(this, userId: int) -> str | None:
        query: str = "SELECT alias from timezones WHERE user = ?"
        return await this.executeGetStrQuery(query, (userId,))

    async def getUserByAlias(this, alias: str) -> str | None:
        query: str = "SELECT user from timezones WHERE alias = ?"
        return await this.executeGetStrQuery(query, (alias,))

    async def getTimeZoneByAlias(this, alias: str) -> str | None:
        query: str = "SELECT timezone from timezones WHERE alias = ?"
        return await this.executeGetStrQuery(query, (alias,))

    async def addTzOverride(this, uuid: str, timezone: str) -> bool:
        query: str = "INSERT into tz_overrides (uuid, timezone) VALUES (?, ?) ON CONFLICT DO UPDATE SET timezone = ?"
        mdbQuery: str = "INSERT into tz_overrides (uuid, timezone) VALUES (%s, %s) ON DUPLICATE KEY UPDATE timezone = ?"

        return await this.executeSetQuery(query, mdbQuery, (uuid, timezone.replace(" ", "_"), timezone.replace(" ", "_")))

    async def getTzOverrides(this) -> dict[str, str] | None:
        query: str = "SELECT uuid, timezone from tz_overrides"

        cursor = await this.conn.execute(query)
        await this.conn.commit()
        if not (val := await cursor.fetchall()):
            return None

        return {value[0]: value[1] for value in val}

    async def getTzOverrideByUUID(this, uuid: str) -> str | None:
        query: str = "SELECT timezone from tz_overrides WHERE uuid = ?"
        return await this.executeGetStrQuery(query, (uuid,))

    async def removeTzOverride(this, uuid: str) -> bool:
        query: str = "DELETE FROM tz_overrides WHERE uuid = ?"
        return await this.executeSetQuery(query, query.replace("?", "%s"), (uuid,))

    async def assignUUIDToUserId(this, uuid: str, userId: int, timezone: str) -> bool:
        query: str = "INSERT INTO timezones (user, uuid, timezone, alias) VALUES (?, ?, ?, ?) ON CONFLICT(user) DO UPDATE SET uuid = ?;"
        mdbQuery: str = "INSERT INTO timezones (user, uuid, timezone, alias) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE uuid = %s;"

        return await this.executeSetQuery(query, mdbQuery, (userId, uuid, timezone.replace(" ", "_"), uuid, uuid))

    async def unassignUUIDFromUserId(this, userId: int) -> bool:
        query: str = "UPDATE timezones SET uuid = NULL WHERE user = ?"
        return await this.executeSetQuery(query, query.replace("?", "%s"), (userId,))

    async def getUUIDByUserId(this, userId: int) -> str | None:
        query: str = "SELECT uuid from timezones WHERE user = ?"
        return await this.executeGetStrQuery(query, (userId,))

    async def getUserIdByUUID(this, uuid: str) -> str | None:
        query: str = "SELECT user from timezones WHERE uuid = ?"
        return await this.executeGetStrQuery(query, (uuid,))

    async def getTimezoneByUUID(this, uuid: str) -> str | None:
        query: str = "SELECT timezone from timezones WHERE uuid = ?"
        return await this.executeGetStrQuery(query, (uuid,))
