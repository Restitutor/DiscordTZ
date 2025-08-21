import asyncio

import aiosqlite


class Database:
    def __init__(this, filename: str) -> None:
        this.filename = filename

        asyncio.create_task(this._postInit())

    async def _postInit(this) -> None:
        this.conn = await aiosqlite.connect(this.filename)

    async def setTimezone(this, userId: int, timezone: str, alias: str) -> bool:
        query: str = "INSERT into timezones (user, timezone, alias) VALUES (?, ?, ?)\
                 ON CONFLICT DO UPDATE SET timezone = ?, alias = ?;"

        cursor = await this.conn.execute(query, (userId, timezone.replace(" ", "_"), alias, timezone.replace(" ", "_"), alias))
        await this.conn.commit()
        return cursor.rowcount != 0

    async def setAlias(this, userId: int, alias: str) -> bool:
        query: str = "UPDATE timezones SET alias = ? WHERE user = ?;"

        cursor = await this.conn.execute(query, (alias, userId))
        await this.conn.commit()
        return cursor.rowcount != 0

    async def getTimeZone(this, userId: int) -> str | None:
        query: str = "SELECT timezone from timezones WHERE user = ?"

        cursor = await this.conn.execute(query, (userId,))
        await this.conn.commit()
        if not (val := await cursor.fetchone()):
            return None

        return str(val[0])

    async def getAlias(this, userId: int) -> str | None:
        query: str = "SELECT alias from timezones WHERE user = ?"

        cursor = await this.conn.execute(query, (userId,))
        await this.conn.commit()
        if not (val := await cursor.fetchone()):
            return None

        return str(val[0])

    async def getUserByAlias(this, alias: str) -> str | None:
        query: str = "SELECT user from timezones WHERE alias = ?"

        cursor = await this.conn.execute(query, (alias,))
        await this.conn.commit()
        if not (val := await cursor.fetchone()):
            return None

        return str(val[0])

    async def getTimeZoneByAlias(this, alias: str) -> str | None:
        query: str = "SELECT timezone from timezones WHERE alias = ?"

        cursor = await this.conn.execute(query, (alias,))
        await this.conn.commit()
        if not (val := await cursor.fetchone()):
            return None

        return str(val[0])

    async def getAllAliases(this) -> list[str] | None:
        query: str = "SELECT alias from timezones"

        cursor = await this.conn.execute(query)
        await this.conn.commit()
        if not (val := await cursor.fetchall()):
            return None

        return [str(value[0]) for value in val]

    async def addTzOverride(this, uuid: str, timezone: str) -> bool:
        query: str = "INSERT into tz_overrides (uuid, timezone) VALUES (?, ?) ON CONFLICT DO UPDATE SET timezone = ?"

        cursor = await this.conn.execute(query, (uuid, timezone.replace(" ", "_"), timezone.replace(" ", "_")))
        await this.conn.commit()
        return cursor.rowcount != 0

    async def getTzOverrides(this) -> dict[str, str] | None:
        query: str = "SELECT uuid, timezone from tz_overrides"

        cursor = await this.conn.execute(query)
        await this.conn.commit()
        if not (val := await cursor.fetchall()):
            return None

        return {value[0]: value[1] for value in val}

    async def getTzOverrideByUUID(this, uuid: str) -> str | None:
        query: str = "SELECT timezone from tz_overrides WHERE uuid = ?"

        cursor = await this.conn.execute(query, (uuid,))
        await this.conn.commit()
        if not (val := await cursor.fetchone()):
            return None

        return str(val[0])

    async def removeTzOverride(this, uuid: str) -> bool:
        query: str = "DELETE FROM tz_overrides WHERE uuid = ?"

        cursor = await this.conn.execute(query, (uuid,))
        await this.conn.commit()
        return cursor.rowcount != 0

    async def assignUUIDToUserId(this, uuid: str, userId: int, timezone: str) -> bool:
        query: str = "INSERT INTO timezones (user, uuid, timezone, alias) VALUES (?, ?, ?, ?) ON CONFLICT(user) DO UPDATE SET uuid = ?;"

        cursor = await this.conn.execute(query, (userId, uuid, timezone.replace(" ", "_"), uuid, uuid))
        await this.conn.commit()
        return cursor.rowcount != 0

    async def unassignUUIDFromUserId(this, userId: int) -> bool:
        query: str = "UPDATE timezones SET uuid = NULL WHERE user = ?"

        cursor = await this.conn.execute(query, (userId,))
        await this.conn.commit()
        return cursor.rowcount != 0

    async def getUUIDByUserId(this, userId: int) -> str | None:
        query: str = "SELECT uuid from timezones WHERE user = ?"

        cursor = await this.conn.execute(query, (userId,))
        await this.conn.commit()
        if not (val := await cursor.fetchone()):
            return None

        return str(val[0])

    async def getUserIdByUUID(this, uuid: str) -> str | None:
        query: str = "SELECT user from timezones WHERE uuid = ?"

        cursor = await this.conn.execute(query, (uuid,))
        await this.conn.commit()
        if not (val := await cursor.fetchone()):
            return None

        return str(val[0])

    async def getTimezoneByUUID(this, uuid: str) -> str | None:
        query: str = "SELECT timezone from timezones WHERE uuid = ?"

        cursor = await this.conn.execute(query, (uuid,))
        await this.conn.commit()
        if not (val := await cursor.fetchone()):
            return None

        return str(val[0])
