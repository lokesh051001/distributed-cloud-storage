from app.security import create_access_token, verify_access_token
from app.utils.crypto_utils import decrypt_bytes, encrypt_bytes


def test_token_roundtrip():
    token = create_access_token("admin")
    assert verify_access_token(token) == "admin"


def test_encrypt_decrypt_roundtrip():
    raw = b"distributed-system-test-data"
    encrypted = encrypt_bytes(raw)
    assert encrypted != raw
    assert decrypt_bytes(encrypted) == raw
