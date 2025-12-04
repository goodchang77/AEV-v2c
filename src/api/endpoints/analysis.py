# src/api/endpoints/analysis.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.services.risk_assessment import RiskAssessmentEngine
from src.services.valuation_models import DCFValuationModel
from src.services.peer_analysis import PeerAnalyzer
from src.schemas.requests import DCFRequest, PeerComparisonRequest, RiskAssessmentRequest
from src.schemas.responses import StandardResponse

router = APIRouter(prefix="/api/v1/analysis", tags=["Analysis"])

@router.post("/dcf", response_model=StandardResponse)
async def calculate_dcf_valuation(
    request: DCFRequest,
    db: Session = Depends(get_db)
):
    """
    DCF估值計算
    
    請求參數:
    - company_id: 股票代號(4碼)
    - revenue_growth_rates: 收入成長率預測(3-10年)
    - terminal_growth_rate: 永續成長率(0-10%)
    - discount_rate: 折現率(1-30%)
    """
    try:
        model = DCFValuationModel(db)
        result = model.calculate_enterprise_value(
            company_id=request.company_id,
            revenue_growth_rates=request.revenue_growth_rates,
            terminal_growth_rate=request.terminal_growth_rate,
            discount_rate=request.discount_rate
        )
        
        # 敏感性分析
        sensitivity = model.perform_sensitivity_analysis(
            base_result=result,
            discount_rate_range=(-0.02, 0.02),  # ±2%
            growth_rate_range=(-0.01, 0.01)     # ±1%
        )
        
        return StandardResponse(
            success=True,
            data={
                "valuation": result,
                "sensitivity_analysis": sensitivity
            },
            meta={
                "company_id": request.company_id,
                "model_type": "DCF",
                "calculation_date": datetime.now().isoformat()
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/peer-comparison", response_model=StandardResponse)
async def peer_comparison_analysis(
    request: PeerComparisonRequest,
    db: Session = Depends(get_db)
):
    """同業比較分析"""
    try:
        analyzer = PeerAnalyzer(db)
        result = analyzer.analyze_peer_comparison(
            company_id=request.company_id,
            peer_selection_method=request.peer_selection_method
        )
        
        return StandardResponse(
            success=True,
            data=result,
            meta={
                "company_id": request.company_id,
                "num_peers": len(result["peers"]),
                "analysis_date": datetime.now().isoformat()
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/risk-assessment", response_model=StandardResponse)
async def risk_assessment(
    request: RiskAssessmentRequest,
    db: Session = Depends(get_db)
):
    """綜合風險評估"""
    try:
        engine = RiskAssessmentEngine(db)
        result = engine.assess_overall_risk(company_id=request.company_id)
        
        return StandardResponse(
            success=True,
            data=result,
            meta={
                "company_id": request.company_id,
                "assessment_date": datetime.now().isoformat(),
                "risk_grade": result["risk_grade"]
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))