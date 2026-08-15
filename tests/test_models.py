"""
資料層 ORM 對齊測試（不依賴 DB）
驗證 src/models.py 與 01_create_tables.sql / 03_valuation_and_stock.sql 的欄位對齊，
防止未來再次漂移（Phase 2）。
"""

from sqlalchemy import BigInteger
from sqlalchemy.dialects.postgresql import UUID

from src import models


def _cols(cls):
    return {c.name for c in cls.__table__.columns}


def test_user_uses_uuid_primary_key():
    assert isinstance(models.User.__table__.c.user_id.type, UUID)
    assert isinstance(models.UserWatchlist.__table__.c.user_id.type, UUID)


def test_user_has_full_column_set():
    cols = _cols(models.User)
    for name in ("full_name", "permissions", "is_verified", "login_count",
                 "timezone", "language", "preferences", "updated_at", "role"):
        assert name in cols, f"users 缺少欄位 {name}"


def test_user_watchlist_columns():
    cols = _cols(models.UserWatchlist)
    for name in ("watchlist_name", "notes", "priority", "company_id", "added_at"):
        assert name in cols, f"user_watchlists 缺少欄位 {name}"


def test_valuation_result_model_exists():
    cols = _cols(models.ValuationResult)
    for name in ("company_id", "valuation_date", "model_type", "fair_value",
                 "current_price", "upside_downside", "sensitivity_analysis",
                 "assumptions", "discount_rate", "growth_rate", "terminal_value"):
        assert name in cols, f"valuation_results 缺少欄位 {name}"


def test_stock_price_model_exists():
    cols = _cols(models.StockPrice)
    for name in ("company_id", "trade_date", "open_price", "high_price",
                 "low_price", "close_price", "volume", "adj_close"):
        assert name in cols, f"stock_prices 缺少欄位 {name}"


def test_company_outstanding_shares_is_biginteger():
    assert isinstance(models.Company.__table__.c.outstanding_shares.type, BigInteger)
