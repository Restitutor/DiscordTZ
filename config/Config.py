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
    tzTableName: str
    overridesTableName: str


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


@dataclass_json
@dataclass
class Config:
    token: str
    ownerId: int
    maxmind: MaxmindConfig
    mariadbDetails: MariaDBConfig
    server: ServerConfig
    packetLogs: PacketLogsConfig
