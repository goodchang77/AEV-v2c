"""
設定安全性測試：正式環境必須 fail-closed。
不需要 Postgres / Redis（僅建立設定物件）。
"""

import secrets

import pytest
from pydantic import ValidationError

from src.core import config as config_module
from src.core.config import (
    DevelopmentSettings,
    ProductionSettings,
    get_settings,
    is_insecure_secret_key,
    resolve_environment,
)

_ENV_KEYS = (
    "ENVIRONMENT", "ENV", "SECRET_KEY", "DEBUG",
    "ALLOWED_HOSTS", "ALLOWED_ORIGINS",
)


@pytest.fixture
def clean_env(monkeypatch):
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    get_settings.cache_clear()
    yield monkeypatch
    get_settings.cache_clear()


def _strong_key() -> str:
    return secrets.token_hex(32)


def test_resolve_environment_prefers_environment(clean_env):
    clean_env.setenv("ENVIRONMENT", "testing")
    clean_env.setenv("ENV", "production")
    assert resolve_environment() == "testing"


def test_resolve_environment_falls_back_to_legacy_env(clean_env):
    clean_env.setenv("ENV", "production")
    assert resolve_environment() == "production"


def test_resolve_environment_default_is_development(clean_env):
    assert resolve_environment() == "development"


def test_development_behaviour_unchanged(clean_env):
    s = get_settings()
    assert isinstance(s, DevelopmentSettings)
    assert s.DEBUG is True


@pytest.mark.parametrize(
    "bad_key",
    [
        None,  # 未設定 → 使用程式碼內建 dev 預設值
        "short",
        config_module._DEV_DEFAULT_SECRET_KEY,
        "ci_secret_key_0123456789abcdef0123456789abcdef",
        "change-me-64-char-random-string-xxxxxxxxxxxxxxxxxx",
        "your-secret-key-goes-here-0123456789abcdef",
        "EXAMPLE_secret_key_0123456789abcdef0123456789",
    ],
)
def test_production_rejects_weak_or_default_secret_key(clean_env, bad_key):
    clean_env.setenv("ENVIRONMENT", "production")
    clean_env.setenv("ALLOWED_HOSTS", "api.example-host.test")
    if bad_key is not None:
        clean_env.setenv("SECRET_KEY", bad_key)
    with pytest.raises(ValidationError) as exc:
        get_settings()
    assert "SECRET_KEY" in str(exc.value)
    # 錯誤訊息不得回顯金鑰值
    if bad_key and len(bad_key) > 8:
        assert bad_key not in str(exc.value)


def test_production_via_legacy_env_var_is_enforced(clean_env):
    """部署範本只設定 ENV=production 時，也必須走正式環境檢查。"""
    clean_env.setenv("ENV", "production")
    with pytest.raises(ValidationError):
        get_settings()


def test_production_with_strong_key_succeeds_and_forces_debug_off(clean_env):
    clean_env.setenv("ENV", "production")
    clean_env.setenv("SECRET_KEY", _strong_key())
    clean_env.setenv("DEBUG", "true")
    clean_env.setenv("ALLOWED_HOSTS", "api.example-host.test, www.example-host.test")
    clean_env.setenv("ALLOWED_ORIGINS", "https://www.example-host.test")
    s = get_settings()
    assert isinstance(s, ProductionSettings)
    assert s.DEBUG is False
    assert s.ALLOWED_HOSTS[:2] == ["api.example-host.test", "www.example-host.test"]
    assert "localhost" in s.ALLOWED_HOSTS and "127.0.0.1" in s.ALLOWED_HOSTS
    assert s.ALLOWED_ORIGINS == ["https://www.example-host.test"]


def test_production_requires_allowed_hosts(clean_env):
    clean_env.setenv("ENVIRONMENT", "production")
    clean_env.setenv("SECRET_KEY", _strong_key())
    with pytest.raises(ValidationError) as exc:
        get_settings()
    assert "ALLOWED_HOSTS" in str(exc.value)


def test_production_rejects_wildcards(clean_env):
    clean_env.setenv("ENVIRONMENT", "production")
    clean_env.setenv("SECRET_KEY", _strong_key())
    clean_env.setenv("ALLOWED_HOSTS", "*")
    with pytest.raises(ValidationError):
        get_settings()
    get_settings.cache_clear()
    clean_env.setenv("ALLOWED_HOSTS", "api.example-host.test")
    clean_env.setenv("ALLOWED_ORIGINS", "*")
    with pytest.raises(ValidationError):
        get_settings()


def test_production_origins_default_to_none(clean_env):
    clean_env.setenv("ENVIRONMENT", "production")
    clean_env.setenv("SECRET_KEY", _strong_key())
    clean_env.setenv("ALLOWED_HOSTS", "api.example-host.test")
    assert get_settings().ALLOWED_ORIGINS == []


def test_is_insecure_secret_key_accepts_random_hex():
    assert is_insecure_secret_key(_strong_key()) is False
    assert is_insecure_secret_key("") is True
