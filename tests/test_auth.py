"""
認證單元測試（不依賴 DB）
驗證密碼雜湊與 JWT 產出/解析邏輯。
"""

from jose import jwt

from src.core.config import get_settings
from src.api.endpoints.auth import (
    _hash_password,
    _verify_password,
    create_access_token,
)


def test_password_hash_and_verify():
    hashed = _hash_password("password123")
    assert hashed != "password123"
    assert _verify_password("password123", hashed)
    assert not _verify_password("wrong", hashed)


def test_create_access_token_payload():
    token = create_access_token("00000000-0000-0000-0000-000000000000", "alice")
    payload = jwt.decode(token, get_settings().SECRET_KEY, algorithms=[get_settings().ALGORITHM])
    assert payload["sub"] == "00000000-0000-0000-0000-000000000000"
    assert payload["username"] == "alice"
    assert "exp" in payload
