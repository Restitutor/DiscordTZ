import asyncio
from collections.abc import Callable
from typing import Any

import aiomysql
import aiosqlite

from config.Config import MariaDBConfig
from shell.Logger import Logger


class SQLiteToMariaDBSync:
    def __init__(this, sqlitePath: str, mariadbConfig: MariaDBConfig, primaryKeys: dict[str, str]) -> None:
        this.sqlitePath: str = sqlitePath
        this.mariadbConfig: MariaDBConfig = mariadbConfig
        this.primaryKeys: dict[str, str] = primaryKeys
        this.sqliteConn: aiosqlite.Connection | None = None
        this.mariadbConn: aiomysql.Connection | None = None

    async def connect(this) -> None:
        this.sqliteConn = await aiosqlite.connect(this.sqlitePath)
        this.mariadbConn = await aiomysql.connect(this.mariadbConfig)

    async def close(this) -> None:
        if this.sqliteConn:
            await this.sqliteConn.close()
        if this.mariadbConn:
            this.mariadbConn.close()

    @classmethod
    async def cronJob(cls, sqlitePath: str, mariadbConfig: MariaDBConfig, time: int = 15) -> None:
        instance = cls(sqlitePath, mariadbConfig, {"timezones": "user", "tz_overrides": "uuid"})
        await instance.connect()

        while True:
            await asyncio.sleep(time * 60)
            await instance.syncAllTables()

    async def getSqliteTables(this) -> list[str]:
        async with this.sqliteConn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def tableExistsInMariadb(this, table: str) -> bool:
        async with this.mariadbConn.cursor() as cur:
            await cur.execute("SHOW TABLES;")
            tables = await cur.fetchall()
            return (table,) in tables

    async def getTableColumns(this, table: str) -> list[str]:
        async with this.sqliteConn.execute(f"PRAGMA table_info({table});") as cursor:
            rows = await cursor.fetchall()
            return [row[1] for row in rows]

    def _keyFunc(this, primaryKey: str, columns: list[str]) -> Callable[[Any], Any]:
        if isinstance(primaryKey, list):
            return lambda row: tuple(row[col] if isinstance(row, dict) else row[columns.index(col)] for col in primaryKey)
        return lambda row: row[primaryKey] if isinstance(row, dict) else row[columns.index(primaryKey)]

    async def getPrimaryKey(this, table: str) -> str | None:
        options = this.primaryKeys.get(table)
        if not options:
            return None

        columns = await this.getTableColumns(table)

        pk1, pk2 = options

        def hasPk(pk: str) -> bool:
            if isinstance(pk, list):
                return all(col in columns for col in pk)
            return pk in columns

        if hasPk(pk1):
            return pk1
        if hasPk(pk2):
            return pk2
        return None

    async def fetchDataDict(
        this,
        conn: aiosqlite.Connection | aiomysql.Connection,
        table: str,
        columns: list[str],
        dbType: str,
        primaryKey: str,
    ) -> dict[Any, dict[str, Any]]:
        colStr = ", ".join(f"`{col}`" if dbType == "mysql" else f'"{col}"' for col in columns)
        query = f"SELECT {colStr} FROM `{table}`" if dbType == "mysql" else f"SELECT {colStr} FROM {table}"  # noqa: S608
        data: dict[Any, dict[str, Any]] = {}

        key_func = this._keyFunc(primaryKey, columns)

        if dbType == "sqlite":
            async with conn.execute(query) as cursor:
                async for row in cursor:
                    rowDict = dict(zip(columns, row, strict=False))
                    key = key_func(rowDict)
                    data[key] = rowDict
        else:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query)
                rows = await cur.fetchall()
                for row in rows:
                    key = key_func(row)
                    data[key] = row

        return data

    async def insertRow(this, table: str, row: dict[str, Any]) -> None:
        columns = ", ".join(f"`{k}`" for k in row)
        placeholders = ", ".join(["%s"] * len(row))
        values = tuple(row.values())

        query = f"INSERT INTO `{table}` ({columns}) VALUES ({placeholders})"  # noqa: S608
        async with this.mariadbConn.cursor() as cur:
            await cur.execute(query, values)

    async def updateRow(this, table: str, row: dict[str, Any], primaryKey: str) -> None:
        if isinstance(primaryKey, list):
            whereClause = " AND ".join(f"`{col}` = %s" for col in primaryKey)
            setCols = [k for k in row if k not in primaryKey]
            setClause = ", ".join(f"`{k}` = %s" for k in setCols)
            values = [row[col] for col in setCols] + [row[col] for col in primaryKey]
        else:
            whereClause = f"`{primaryKey}` = %s"
            setCols = [k for k in row if k != primaryKey]
            setClause = ", ".join(f"`{k}` = %s" for k in setCols)
            values = [row[k] for k in setCols] + [row[primaryKey]]

        query = f"UPDATE `{table}` SET {setClause} WHERE {whereClause}"  # noqa: S608
        async with this.mariadbConn.cursor() as cur:
            await cur.execute(query, values)

    async def syncTable(this, table: str) -> None:
        if not await this.tableExistsInMariadb(table):
            Logger.error(f"Skipping table '{table}' (not found in MariaDB)")
            return

        primaryKey = await this.getPrimaryKey(table)
        if primaryKey is None:
            Logger.error(f"Skipping table '{table}' (primary key not found or missing columns)")
            return

        Logger.log(f"Syncing table: {table}")
        columns = await this.getTableColumns(table)

        sqliteData = await this.fetchDataDict(this.sqliteConn, table, columns, dbType="sqlite", primaryKey=primaryKey)
        mariadbData = await this.fetchDataDict(this.mariadbConn, table, columns, dbType="mysql", primaryKey=primaryKey)

        inserts = 0
        updates = 0

        for pk, row in sqliteData.items():
            if pk not in mariadbData:
                await this.insertRow(table, row)
                inserts += 1
            elif row != mariadbData[pk]:
                await this.updateRow(table, row, primaryKey)
                updates += 1

        await this.mariadbConn.commit()
        Logger.success(f"{table}: Inserted = {inserts}, Updated = {updates}")

    async def syncAllTables(this) -> None:
        tables = await this.getSqliteTables()
        for table in tables:
            await this.syncTable(table)
