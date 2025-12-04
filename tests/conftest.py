# 建立 testsconftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models import Base
from src.core.database import get_db

@pytest.fixture(scope=session)
def test_db()
    測試資料庫fixture
    engine = create_engine(sqlitememory)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    yield TestingSessionLocal()
    Base.metadata.drop_all(engine)

@pytest.fixture
def sample_company_data()
    基於台積電財報的測試資料
    return {
        company_id 2330,
        name 台灣積體電路,
        revenue 573_584_904_000,  # 573.58億(從文件中提取)
        net_income 127_009_731_000,  # 1270億淨利
        total_assets 573_584_904_000,
        total_equity 507_981_284_000,
        current_assets 193_676_010_000,
        current_liabilities 42_905_154_000
    }