import hashlib

from app.config.settings import settings


def _keystream(length: int) -> bytes:
    seed = settings.encryption_key.encode("utf-8")
    stream = b""
    counter = 0
    while len(stream) < length:
        stream += hashlib.sha256(seed + str(counter).encode("utf-8")).digest()
        counter += 1
    return stream[:length]


def encrypt_bytes(data: bytes) -> bytes:
    key = _keystream(len(data))
    return bytes(a ^ b for a, b in zip(data, key))


def decrypt_bytes(data: bytes) -> bytes:
    return encrypt_bytes(data)
