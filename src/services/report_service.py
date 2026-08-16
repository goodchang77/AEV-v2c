"""
報告生成服務 (Report Service)
==============================

財務分析報告生成：Markdown / PDF（PyMuPDF）與 Excel（openpyxl）匯出。
"""

from datetime import datetime
import io
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ReportService:
    """報告生成服務"""

    def __init__(self, db_session=None):
        self.db_session = db_session

    # ------------------------------------------------------------------
    # 資料蒐集
    # ------------------------------------------------------------------
    async def _gather(self, company_id: str) -> Dict[str, Any]:
        from src.services.data_service import CompanyDataService, FinancialDataService
        from src.services.risk_assessment import RiskAssessmentEngine
        from src.core.cache import get_cache_manager
        from src.services.financial_service import (
            FinancialDataService as HealthService,  # 有 calculate_financial_health
        )

        company = await CompanyDataService().get_company_basic_info(company_id)
        fin_svc = FinancialDataService()
        ratios = await fin_svc.get_financial_ratios(company_id)
        trend = await fin_svc.get_financial_trend(company_id, periods=4)

        cache_manager = await get_cache_manager()
        health_svc = HealthService(cache_manager)
        health = await health_svc.calculate_financial_health(company_id)

        engine = RiskAssessmentEngine()
        import asyncio
        risk = await asyncio.to_thread(engine.assess_overall_risk, company_id)

        return {
            "company": company or {},
            "ratios": ratios or {},
            "health": health or {},
            "trend": trend or {},
            "risk": risk or {},
        }

    # ------------------------------------------------------------------
    # Markdown 生成
    # ------------------------------------------------------------------
    def _build_markdown(self, company_id: str, data: Dict[str, Any], report_type: str) -> str:
        c = data["company"]
        r = data["ratios"]
        h = data["health"]
        risk = data["risk"]
        lines = [
            f"# {c.get('company_name', company_id)}（{company_id}）財務分析報告",
            f"生成時間：{datetime.utcnow().isoformat()}",
            "",
            "## 1. 公司基本資料",
            f"- 產業：{c.get('industry_name') or c.get('industry_code') or '—'}",
            f"- 市場：{c.get('market_type') or '—'}",
            f"- 上市日期：{c.get('listing_date') or '—'}",
            f"- 資本額：{c.get('capital_amount') or '—'}",
            "",
            "## 2. 財務比率（最新期）",
            f"- ROE：{(r.get('roe') or 0) * 100:.2f}%｜ROA：{(r.get('roa') or 0) * 100:.2f}%",
            f"- 毛利率：{(r.get('gross_margin') or 0) * 100:.2f}%｜淨利率：{(r.get('net_margin') or 0) * 100:.2f}%",
            f"- 流動比率：{r.get('current_ratio') or '—'}｜負債比率：{(r.get('debt_to_asset_ratio') or 0) * 100:.2f}%",
            f"- 本益比：{r.get('pe_ratio') or '—'}｜股價淨值比：{r.get('pb_ratio') or '—'}",
            "",
            "## 3. 財務健康度",
            f"- 綜合評級：{h.get('overall_grade') or '—'}（{h.get('overall_score') or '—'}/100）",
        ]
        for k, v in (h.get("detailed_scores") or {}).items():
            lines.append(f"- {k}：{v}")
        lines += ["", "## 4. 風險評估"]
        lines.append(f"- 綜合風險分數：{risk.get('overall_risk_score')}（{risk.get('risk_grade')}，{risk.get('risk_level')}）")
        distress = (risk.get("risk_breakdown") or {}).get("financial_distress") or {}
        lines.append(f"- Altman Z-Score：{distress.get('z_score')}（{distress.get('risk_level')}）")
        for concern in risk.get("key_concerns") or []:
            lines.append(f"- ⚠️ {concern}")
        lines += ["", "## 5. 建議"]
        for rec in risk.get("recommendations") or []:
            lines.append(f"- {rec}")

        if report_type != "summary":
            trend = data["trend"]
            st = (trend.get("statements_trend") or [])[-4:]
            lines += ["", "## 6. 營收趨勢"]
            for row in st:
                lines.append(
                    f"- {row.get('period')}：營收 {row.get('revenue'):,.0f}｜淨利 {row.get('net_income'):,.0f}（EPS {row.get('eps')}）"
                )
            ga = trend.get("growth_analysis") or {}
            lines.append(f"- 營收成長：{ga.get('revenue_growth')}%｜淨利成長：{ga.get('net_income_growth')}%")

        lines += ["", "*本報告由 AEV-v2c 系統自動生成，資料僅供參考，不構成投資建議。*"]
        return "\n".join(lines)

    def _render_pdf(self, markdown_text: str) -> bytes:
        import fitz  # PyMuPDF

        doc = fitz.open()
        page = doc.new_page(width=595, height=842)  # A4
        y = 50.0
        for line in markdown_text.split("\n"):
            if y > 800:
                page = doc.new_page(width=595, height=842)
                y = 50.0
            try:
                page.insert_text((50, y), line, fontname="china-t", fontsize=10)
            except Exception:
                page.insert_text((50, y), line, fontsize=10)
            y += 16
        buf = io.BytesIO()
        doc.save(buf)
        doc.close()
        return buf.getvalue()

    # ------------------------------------------------------------------
    # 對外介面
    # ------------------------------------------------------------------
    async def generate_financial_report(
        self,
        company_id: str,
        report_type: str = "comprehensive",
        format: str = "pdf",
    ) -> Dict[str, Any]:
        """生成財務分析報告（markdown/json 回內文；pdf 回 bytes）"""
        data = await self._gather(company_id)
        if not data["company"]:
            return {"status": "error", "message": f"找不到公司 {company_id}"}

        markdown = self._build_markdown(company_id, data, report_type)

        if format in ("markdown", "md", "json"):
            return {
                "status": "success",
                "company_id": company_id,
                "report_type": report_type,
                "format": "markdown",
                "content": markdown,
                "timestamp": datetime.utcnow().isoformat(),
            }

        pdf_bytes = self._render_pdf(markdown)
        return {
            "status": "success",
            "company_id": company_id,
            "report_type": report_type,
            "format": "pdf",
            "content_bytes": pdf_bytes,
            "filename": f"report_{company_id}.pdf",
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def generate_valuation_report(
        self,
        company_id: str,
        valuation_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """生成評價報告（Markdown）"""
        markdown = "\n".join(
            [
                f"# {company_id} 評價報告",
                f"生成時間：{datetime.utcnow().isoformat()}",
                "",
                "## 評價結果",
                f"- 公允價值每股：{valuation_results.get('fair_value_per_share')}",
                f"- 評價方法：{valuation_results.get('valuation_method')}",
                "",
            ]
        )
        return {"status": "success", "format": "markdown", "content": markdown}

    async def export_to_excel(self, data: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """匯出財務資料為 Excel（openpyxl，回 bytes）"""
        from openpyxl import Workbook
        from openpyxl.styles import Font

        wb = Workbook()
        ws = wb.active
        ws.title = "財務資料"
        ws.append(["指標", "數值"])
        for cell in ws[1]:
            cell.font = Font(bold=True)

        ratios = data.get("ratios") or {}
        for key, value in ratios.items():
            ws.append([key, value])

        buf = io.BytesIO()
        wb.save(buf)
        return {
            "status": "success",
            "format": "xlsx",
            "content_bytes": buf.getvalue(),
            "filename": filename or "financial_data.xlsx",
        }
