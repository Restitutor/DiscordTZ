import os

import mariadb

from shell.Logger import Logger


def defaultTz() -> str:
    temp: list[str] = os.readlink("/etc/localtime").split("/")  # noqa: PTH115
    return f"{temp[-2]}/{temp[-1]}"


class Database:
    conn: mariadb.Connection
    tzTableName: str
    tzOverrideTableName: str
    _connectionDetails: dict

    def __init__(this, connectionDetails: dict):
        this._connectionDetails = connectionDetails

        this._reconnect()
        this.tzTableName = connectionDetails.get("tzTableName")
        this.tzOverrideTableName = connectionDetails.get("overridesTableName")

    def _reconnect(this):
        this.conn = mariadb.connect(
            database=this._connectionDetails.get("database"),
            user=this._connectionDetails.get("user"),
            password=this._connectionDetails.get("password"),
            host=this._connectionDetails.get("host"),
            port=int(this._connectionDetails.get("port")),
            autocommit=bool(this._connectionDetails.get("autocommit")),
        )

    def set(this, userId: int, timezone: str, alias: str) -> bool:
        this._reconnect()
        conn: mariadb.Connection = this.conn
        cursor: mariadb.Cursor = conn.cursor(prepared=True)
        query: str = f"INSERT into {this.tzTableName} (user, timezone, alias) VALUES (%s, %s, %s)\
         ON DUPLICATE KEY UPDATE timezone = VALUES(timezone), alias = VALUES(alias);"

        data: tuple[int, str, str] = (userId, timezone.replace(" ", "_"), alias)

        try:
            cursor.execute(query, data)
            conn.commit()
            return True
        except mariadb.Error as e:
            Logger.error(f"Error while writing data to database: {e}")
            return False

    def setAlias(this, userId: int, alias: str) -> bool:
        this._reconnect()
        conn: mariadb.Connection = this.conn
        cursor: mariadb.Cursor = conn.cursor(prepared=True)
        query: str = f"UPDATE {this.tzTableName} SET alias = %s WHERE user = %s;"

        data: tuple[str, int] = (alias, userId)

        try:
            cursor.execute(query, data)
            conn.commit()
            return cursor.rowcount > 0
        except mariadb.Error as e:
            Logger.error(f"Error while writing data to database: {e}")
            return False

    def getTimeZone(this, userId: int) -> str | None:
        this._reconnect()
        if not isinstance(userId, int):
            return None
        conn: mariadb.Connection = this.conn
        cursor: mariadb.Cursor = conn.cursor(prepared=True)
        query: str = f"SELECT timezone from {this.tzTableName} WHERE user = %s"
        data: list[int] = [userId]

        try:
            cursor.execute(query, data)
            conn.commit()

            result = cursor.fetchone()

            if result:
                return str(result[0])
            else:
                return None

        except mariadb.Error as e:
            Logger.error(f"Failed to get timezone: {e}")
            return None

    def getAlias(this, userId: int) -> str | None:
        this._reconnect()
        if not isinstance(userId, int):
            return None
        conn: mariadb.Connection = this.conn
        cursor: mariadb.Cursor = conn.cursor(prepared=True)
        query: str = f"SELECT alias from {this.tzTableName} WHERE user = %s"
        data: list[int] = [userId]
        try:
            cursor.execute(query, data)
            conn.commit()
            result = cursor.fetchone()
            if result:
                return str(result[0])
            else:
                return None

        except mariadb.Error as e:
            Logger.error(f"Failed to get alias: {e}")
            return None

    def getUserByAlias(this, alias: str) -> str | None:
        this._reconnect()
        conn: mariadb.Connection = this.conn
        cursor: mariadb.Cursor = conn.cursor(prepared=True)
        query: str = f"SELECT user from {this.tzTableName} WHERE alias = %s"
        data: list[str] = [alias]
        try:
            cursor.execute(query, data)
            conn.commit()
            result = cursor.fetchone()
            if result:
                return str(result[0])
            else:
                return None

        except mariadb.Error as e:
            Logger.error(f"Failed to get user by alias: {e}")
            return None

    def getTimeZoneByAlias(this, alias: str) -> str | None:
        this._reconnect()
        conn: mariadb.Connection = this.conn
        cursor: mariadb.Cursor = conn.cursor(prepared=True)
        query: str = f"SELECT timezone from {this.tzTableName} WHERE alias = %s"
        data: list[str] = [alias]
        try:
            cursor.execute(query, data)
            conn.commit()
            result = cursor.fetchone()
            if result:
                return str(result[0])
            else:
                return None

        except mariadb.Error as e:
            Logger.error(f"Failed to get timezone by alias: {e}")
            return None

    def getAllAliases(this) -> list[str] | None:
        this._reconnect()
        conn: mariadb.Connection = this.conn
        cursor: mariadb.Cursor = conn.cursor(prepared=True)
        query: str = f"SELECT alias from {this.tzTableName}"
        try:
            cursor.execute(query)
            conn.commit()
            result = cursor.fetchall()
            aliases = [value[0] for value in result]
            return aliases

        except mariadb.Error as e:
            Logger.error(f"Failed to get all aliases: {e}")
            return None

    def addTzOverride(this, uuid: str, timezone: str) -> bool:
        this._reconnect()
        conn: mariadb.Connection = this.conn
        cursor: mariadb.Cursor = conn.cursor(prepared=True)
        query: str = f"INSERT into {this.tzOverrideTableName} (uuid, timezone) VALUES (%s, %s) ON DUPLICATE KEY UPDATE timezone = VALUES(timezone)"

        data: tuple[str, str] = (uuid, timezone)

        try:
            cursor.execute(query, data)
            conn.commit()
            return True
        except mariadb.Error as e:
            Logger.error(f"Error while writing data to database: {e}")
            return False

    def getTzOverrides(this) -> dict[str, str] | None:
        this._reconnect()
        conn: mariadb.Connection = this.conn
        cursor: mariadb.Cursor = conn.cursor(prepared=True)
        query: str = f"SELECT uuid, timezone from {this.tzOverrideTableName}"
        try:
            cursor.execute(query)
            conn.commit()
            result = cursor.fetchall()
            return {value[0]: value[1] for value in result}

        except mariadb.Error as e:
            Logger.error(f"Failed to get timezone overrides: {e}")
            return None

    def getTzOverrideByUUID(this, uuid: str) -> str | None:
        this._reconnect()
        conn: mariadb.Connection = this.conn
        cursor: mariadb.Cursor = conn.cursor(prepared=True)
        query: str = f"SELECT timezone from {this.tzOverrideTableName} WHERE uuid = %s"
        data: tuple[str] = (uuid,)
        try:
            cursor.execute(query, data)
            conn.commit()
            result = cursor.fetchone()
            return result if result is None else result[0]
        except mariadb.Error as e:
            Logger.error(f"Failed to get timezone override: {e}")
            return None

    def removeTzOverride(this, uuid: str) -> bool:
        this._reconnect()
        conn: mariadb.Connection = this.conn
        cursor: mariadb.Cursor = conn.cursor(prepared=True)
        query: str = f"DELETE FROM {this.tzOverrideTableName} WHERE uuid = %s"
        data: tuple[str] = (uuid,)
        try:
            cursor.execute(query, data)
            conn.commit()
            return True
        except mariadb.Error as e:
            Logger.error(f"Failed to remove timezone override: {e}")
            return False

    def assignUUIDToUserId(this, uuid: str | None, userId: int, timezone: str, alias: str) -> bool:
        this._reconnect()
        conn: mariadb.Connection = this.conn
        cursor: mariadb.Cursor = conn.cursor(prepared=True)
        query: str = "INSERT INTO timezones (user, uuid, timezone, alias) VALUES (%s, %s, %s, %s) ON CONFLICT(user) DO UPDATE SET uuid = %s;"

        data: tuple[int, str, str, str, str] = (userId, uuid, timezone, alias, uuid)
        try:
            cursor.execute(query, data)
            conn.commit()
            return True
        except mariadb.Error as e:
            Logger.error(f"Failed to assign UUID to user: {e}")
            return False

    def unassignUUIDFromUserId(this, userId: int) -> bool:
        this._reconnect()
        conn: mariadb.Connection = this.conn
        cursor: mariadb.Cursor = conn.cursor(prepared=True)
        query: str = f"UPDATE {this.tzOverrideTableName} WHERE SET uuid = NULL WHERE user = %s"

        try:
            cursor.execute(query, (userId,))
            conn.commit()
            return True
        except mariadb.Error as e:
            Logger.error(f"Failed to unassign UUID from user: {e}")
            return False

    def getUUIDByUserId(this, userId: int) -> str | None:
        this._reconnect()
        conn: mariadb.Connection = this.conn
        cursor: mariadb.Cursor = conn.cursor(prepared=True)
        query: str = f"SELECT uuid from {this.tzTableName} WHERE user = %s"
        data: tuple[int] = (userId,)
        try:
            cursor.execute(query, data)
            conn.commit()
            result = cursor.fetchone()
            return result[0]
        except mariadb.Error as e:
            Logger.error(f"Failed to get UUID by user: {e}")
            return None

    def getUserIdByUUID(this, uuid: str):
        this._reconnect()
        conn: mariadb.Connection = this.conn
        cursor: mariadb.Cursor = conn.cursor(prepared=True)
        query: str = f"SELECT user from {this.tzTableName} WHERE uuid = %s"
        data: tuple[str] = (uuid,)
        try:
            cursor.execute(query, data)
            conn.commit()
            result = cursor.fetchone()
            return result if result is None else result[0]
        except mariadb.Error as e:
            Logger.error(f"Failed to get UUID by user: {e}")
            return None

    def getTimezoneByUUID(this, uuid: str) -> str | None:
        this._reconnect()
        conn: mariadb.Connection = this.conn
        cursor: mariadb.Cursor = conn.cursor(prepared=True)
        query: str = f"SELECT timezone from {this.tzTableName} WHERE uuid = %s"
        data = (uuid,)
        try:
            cursor.execute(query, data)
            conn.commit()
            result = cursor.fetchone()
            try:
                return result[0]
            except Exception:
                return result

        except mariadb.Error as e:
            Logger.error(f"Failed to get timezone by UUID: {e}")
            return None
