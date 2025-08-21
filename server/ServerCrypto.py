import os

from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import pad, unpad


def AESDecrypt(encrypted_data: bytes, key: bytes) -> str | None:
    iv = encrypted_data[:16]
    data = bytearray(encrypted_data[16:])

    try:
        cipher = AES.new(key, AES.MODE_CBC, iv=iv)
        decryptedData = cipher.decrypt(data)
        decryptedData = unpad(decryptedData, AES.block_size)
        return decryptedData.decode("utf-8").strip()
    except ValueError:
        return None


def AESEncrypt(message: bytes, key: bytes) -> bytes:
    iv = os.urandom(16)
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)

    paddedMessage = pad(message, AES.block_size)
    encryptedMessage = cipher.encrypt(paddedMessage)
    return iv + encryptedMessage


def RSAEncrypt(message: bytes, key: RSA.RsaKey) -> bytes:
    cipher: PKCS1_OAEP.PKCS1OAEP_Cipher = PKCS1_OAEP.new(key)

    return cipher.encrypt(message)


def RSADecrypt(message: bytes, key: RSA.RsaKey) -> bytes:
    cipher: PKCS1_OAEP.PKCS1OAEP_Cipher = PKCS1_OAEP.new(key)

    return cipher.decrypt(message)
