"""
get_current_user 安全性測試（不依賴 DB：以假 session 取代）。
"""

import uuid
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
import jwt

from src.api.endpoints import auth as auth_module
from src.api.endpoints.auth import create_access_token, get_current_user


class _FakeQuery:
    def __init__(self, result, calls):
        self._result = result
        self._calls = calls

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        self._calls.append("first")
        return self._result


class FakeDB:
    """最小化的 Session 替身：query(...).filter(...).first() 回傳預設使用者"""

    def __init__(self, user=None):
        self.user = user
        self.calls = []

    def query(self, *args, **kwargs):
        return _FakeQuery(self.user, self.calls)

    def close(self):
        pass


def _user(active=True):
    return SimpleNamespace(
        user_id=uuid.uuid4(),
        username="alice",
        email="alice@example.test",
        role="user",
        full_name=None,
        is_active=active,
    )


def _raw_token(payload):
    s = auth_module.settings
    return jwt.encode(payload, s.SECRET_KEY, algorithm=s.ALGORITHM)


def test_active_user_is_accepted():
    user = _user(active=True)
    token = create_access_token(str(user.user_id), user.username)
    assert get_current_user(token=token, db=FakeDB(user)) is user


def test_inactive_user_is_rejected():
    user = _user(active=False)
    token = create_access_token(str(user.user_id), user.username)
    with pytest.raises(HTTPException) as exc:
        get_current_user(token=token, db=FakeDB(user))
    assert exc.value.status_code == 403


@pytest.mark.parametrize(
    "payload",
    [
        {"username": "alice"},                 # 缺 sub
        {"sub": None},
        {"sub": "not-a-uuid"},
        {"sub": 12345},
        {"sub": ["x"]},
    ],
)
def test_missing_or_malformed_sub_is_rejected_without_db_lookup(payload):
    payload = dict(payload, exp=datetime.utcnow() + timedelta(minutes=5))
    db = FakeDB(_user())
    with pytest.raises(HTTPException) as exc:
        get_current_user(token=_raw_token(payload), db=db)
    assert exc.value.status_code == 401
    assert db.calls == []


def test_unknown_user_is_rejected():
    token = create_access_token(str(uuid.uuid4()), "ghost")
    with pytest.raises(HTTPException) as exc:
        get_current_user(token=token, db=FakeDB(None))
    assert exc.value.status_code == 401


def test_token_signed_with_other_key_is_rejected():
    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "exp": datetime.utcnow() + timedelta(minutes=5)},
        "another-key-" + "x" * 40,
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc:
        get_current_user(token=token, db=FakeDB(_user()))
    assert exc.value.status_code == 401


def test_me_endpoint_rejects_inactive_user():
    from src.main import app

    user = _user(active=False)
    app.dependency_overrides[auth_module.get_db] = lambda: FakeDB(user)
    try:
        client = TestClient(app)
        token = create_access_token(str(user.user_id), user.username)
        r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403

        user.is_active = True
        r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["username"] == "alice"
    finally:
        app.dependency_overrides.pop(auth_module.get_db, None)
