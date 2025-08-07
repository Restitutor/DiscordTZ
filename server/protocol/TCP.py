import asyncio

from server.protocol.Client import Client
from server.ServerCrypto import AESEncrypt, RSAEncrypt


class TCPClient(Client):
    def __init__(this, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, aesKey: bytes) -> None:
        this.reader: asyncio.StreamReader = reader
        this.writer: asyncio.StreamWriter = writer
        asyncio.create_task(this.writer.wait_closed())
        super().__init__(this.writer.get_extra_info("peername"), aesKey)

    def send(this, data: bytes) -> None:
        if (this.encrypt):
            data = RSAEncrypt(data, this.rsaKey) if this.rsaKey is not None else AESEncrypt(data, this.aesKey)

        this.writer.write(data)
        asyncio.create_task(this.writer.drain())
