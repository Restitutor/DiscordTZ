import asyncio

import aiosqlite

from shell.Logger import Logger


class ApiKeyDatabase:
    def __init__(this, apiKeysKey: str) -> None:
        this.encryptionKey = apiKeysKey

        asyncio.create_task(this._postInit())

    async def _postInit(this) -> None:
        this.conn = await aiosqlite.connect("apiKeys.db")
        await this.conn.execute(
            """CREATE TABLE IF NOT EXISTS pendingApiKeys
               (
                   base64repr TEXT PRIMARY KEY NOT NULL,
                   messageId  BIGINT           NOT NULL
               );
            """,
            (),
        )
        await this.conn.execute("""CREATE TABLE IF NOT EXISTS apiKeys
                             (
                                 base64repr TEXT PRIMARY KEY NOT NULL
                             );""")

        await this.conn.commit()

    async def addToPending(this, apiKey: str, messageId: int) -> None:
        query = "INSERT INTO pendingApiKeys (base64repr, messageId) VALUES (?, ?)"
        await this.conn.execute(query, (apiKey, messageId))
        await this.conn.commit()

    async def moveToReal(this, apiKey: str) -> None:
        query = "SELECT * FROM pendingApiKeys WHERE base64repr = ?"
        cursor = await this.conn.execute(query, (apiKey,))
        row = await cursor.fetchone()

        if not row:
            Logger.error("Could not find API key to move to.")
            return

        query = "INSERT INTO apiKeys VALUES (?)"
        await cursor.execute(query, (row[0],))
        await cursor.connection.commit()

        query = "DELETE FROM pendingApiKeys WHERE base64repr = ?"
        await cursor.execute(query, (apiKey,))
        await cursor.connection.commit()

    async def getRequestByMsgId(this, msgId: int) -> str:
        query = "SELECT base64repr FROM pendingApiKeys WHERE messageId = ?"

        cursor = await this.conn.execute(query, (msgId,))
        return await cursor.fetchone()[0]

    async def flushRequest(this, apiKey: str) -> None:
        query = "DELETE FROM pendingApiKeys WHERE base64repr = ?"
        cursor = await this.conn.execute(query, (apiKey,))
        await cursor.connection.commit()

    async def isValidKey(this, apiKey: str) -> bool:
        query = "SELECT EXISTS(SELECT 1 FROM apiKeys WHERE base64repr = ?)"

        cursor = await this.conn.execute(query, (apiKey,))
        return await cursor.fetchone()[0]
