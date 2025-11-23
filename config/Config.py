from dataclasses import dataclass

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class MaxmindConfig:
    accountId: int
    token: str


@dataclass_json
@dataclass
class MariaDBConfig:
    database: str
    user: str
    password: str
    host: str
    port: int
    autocommit: bool

    def __dict__(this) -> dict:
        return {
            "host": this.host,
            "user": this.user,
            "password": this.password,
            "db": this.database,
            "port": this.port,
            "autocommit": this.autocommit,
        }


@dataclass_json
@dataclass
class ServerConfig:
    port: int
    apiKeysKey: str
    apiApproveChannelId: int
    devlogRoleId: int


@dataclass_json
@dataclass
class PacketLogsConfig:
    errorChannelId: int
    successChannelId: int
    guildId: int
    whoToPing: int


@dataclass_json
@dataclass
class Config:
    token: str
    ownerId: int
    maxmind: MaxmindConfig
    mariadbDetails: MariaDBConfig
    server: ServerConfig
    packetLogs: PacketLogsConfig
