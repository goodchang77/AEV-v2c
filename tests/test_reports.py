"""
報告生成測試（不依賴 DB）
Markdown 建構、PDF 渲染、Excel 匯出。
"""

import pytest

from src.services.report_service import ReportService


@pytest.fixture
def service():
    return ReportService()


@pytest.fixture
def fake_data():
    return {
        "company": {
            "company_id": "2330",
            "company_name": "台積電",
            "industry_name": "半導體業",
            "market_type": "上市",
            "capital_amount": 25930380458,
        },
        "ratios": {
            "roe": 0.266, "roa": 0.236, "gross_margin": 0.4247,
            "net_margin": 0.1771, "current_ratio": 4.67,
            "debt_to_asset_ratio": 0.1212, "pe_ratio": 25.0, "pb_ratio": 6.0,
        },
        "health": {
            "overall_grade": "普通",
            "overall_score": 77.5,
            "detailed_scores": {"獲利能力": 80, "流動性": 90},
        },
        "risk": {
            "overall_risk_score": 92.8,
            "risk_grade": "A",
            "risk_level": "低風險",
            "risk_breakdown": {"financial_distress": {"z_score": 5.58, "risk_level": "低風險"}},
            "key_concerns": [],
            "recommendations": ["保持穩健財務結構"],
        },
        "trend": {
            "statements_trend": [
                {"period": "2024Q4", "revenue": 663996225, "net_income": 132000000, "eps": 5.08}
            ],
            "growth_analysis": {"revenue_growth": 5.0, "net_income_growth": 8.2},
        },
    }


def test_build_markdown_contains_sections(service, fake_data):
    md = service._build_markdown("2330", fake_data, "comprehensive")
    assert "台積電" in md
    assert "財務比率" in md
    assert "風險評估" in md
    assert "Altman Z-Score" in md
    assert "營收趨勢" in md


def test_build_markdown_summary_is_shorter(service, fake_data):
    md = service._build_markdown("2330", fake_data, "summary")
    assert "台積電" in md
    assert "營收趨勢" not in md


def test_render_pdf(service, fake_data):
    md = service._build_markdown("2330", fake_data, "comprehensive")
    pdf = service._render_pdf(md)
    assert pdf[:5] == b"%PDF-"
    assert len(pdf) > 1000


@pytest.mark.asyncio
async def test_export_to_excel(service, fake_data):
    result = await service.export_to_excel({"ratios": fake_data["ratios"]}, "test.xlsx")
    assert result["status"] == "success"
    assert result["content_bytes"][:2] == b"PK"  # xlsx 是 zip
    assert result["filename"] == "test.xlsx"
