"""
同業比較分析測試（純函式，不依賴 DB）
"""

import pytest

from src.services.peer_analysis import (
    IndustryBenchmark,
    PeerAnalyzer,
    PeerCompanyData,
)


@pytest.fixture
def target() -> PeerCompanyData:
    return PeerCompanyData(
        company_id="2330", company_name="台積電",
        market_cap=25_000_000, revenue=2_000_000, net_income=500_000,
        total_assets=4_000_000, shareholders_equity=3_000_000,
        roe=26.6, roa=23.6, current_ratio=4.67, debt_ratio=12.12,
        net_margin=17.71, pe_ratio=25.0, pb_ratio=6.0, ev_ebitda=15.0,
    )


@pytest.fixture
def peers() -> list:
    def mk(cid, name, roe, roa, cr, debt, nm, pe, pb):
        return PeerCompanyData(
            company_id=cid, company_name=name,
            market_cap=1_000_000, revenue=500_000, net_income=50_000,
            total_assets=1_000_000, shareholders_equity=500_000,
            roe=roe, roa=roa, current_ratio=cr, debt_ratio=debt,
            net_margin=nm, pe_ratio=pe, pb_ratio=pb, ev_ebitda=8.0,
        )

    return [
        mk("2317", "鴻海", 11.0, 4.5, 1.6, 52.0, 2.4, 12.0, 1.5),
        mk("2454", "聯發科", 22.0, 14.0, 1.9, 34.0, 17.7, 18.0, 5.0),
        mk("2303", "聯電", 9.0, 6.0, 2.2, 32.0, 15.5, 11.0, 1.8),
    ]


@pytest.fixture
def benchmark() -> IndustryBenchmark:
    return IndustryBenchmark(
        industry_code="M2300", industry_name="半導體業", company_count=3,
        avg_roe=14.0, avg_roa=8.17, avg_current_ratio=1.9, avg_debt_ratio=39.33,
        avg_gross_margin=40.0, avg_net_margin=11.87, avg_pe_ratio=13.67, avg_pb_ratio=2.77,
        median_roe=11.0, median_roa=6.0, median_current_ratio=1.9, median_debt_ratio=34.0,
        roe_25_percentile=10.0, roe_75_percentile=16.5,
        pe_25_percentile=11.5, pe_75_percentile=15.0,
        debt_25_percentile=33.0, debt_75_percentile=43.0,
        roe_std_dev=5.6, roa_std_dev=4.1,
    )


def test_analyze_peer_comparison(target, peers, benchmark):
    analyzer = PeerAnalyzer()
    result = analyzer.analyze_peer_comparison(target, peers, benchmark)
    assert result.target_company_id == "2330"
    assert len(result.peer_companies) == 3
    assert isinstance(result.rankings, dict) and len(result.rankings) > 0
    assert isinstance(result.performance_ratings, dict) and len(result.performance_ratings) > 0


def test_generate_report_has_composite_score(target, peers, benchmark):
    analyzer = PeerAnalyzer()
    result = analyzer.analyze_peer_comparison(target, peers, benchmark)
    report = analyzer.generate_peer_comparison_report(result)
    score = report["executive_summary"]["composite_score"]
    assert 0 <= score <= 100
    assert report["executive_summary"]["peer_count"] == 3
    assert len(report["peer_companies"]) == 3
