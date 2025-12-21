import asyncio

from server.ServerCrypto import AESEncrypt
from server.protocol.Client import Client


class TCPClient(Client):
    def __init__(this, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, aesKey: bytes) -> None:
        this.reader: asyncio.StreamReader = reader
        this.writer: asyncio.StreamWriter = writer
        super().__init__(this.writer.get_extra_info("peername"), aesKey)

    async def send(this, data: bytes) -> None:
        if this.aesKey:
            data = AESEncrypt(data, this.aesKey)

        this.writer.write(data)
        await this.writer.drain()
        this.writer.close()
        await this.writer.wait_closed()
