"""
投資組合 API 端點
Portfolio API Endpoints
=======================

需 JWT 認證（Authorization: Bearer <token>）。
- GET    /portfolio/positions            列出部位
- POST   /portfolio/positions            新增/更新部位
- DELETE /portfolio/positions/{company}  刪除部位
- GET    /portfolio/summary              組合總覽（成本/市值/損益 + 最新 ROE/PE）
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.api.endpoints.auth import get_current_user, get_db
from src.models import Company, PortfolioPosition, User
from src.schemas.responses import StandardResponse

router = APIRouter()


class PositionInput(BaseModel):
    company_id: str = Field(..., pattern=r"^\d{4}$")
    shares: float = Field(..., ge=0, description="持有股數")
    cost_basis: float = Field(..., ge=0, description="每股成本")
    current_price: Optional[float] = Field(None, ge=0, description="最新股價（選填）")
    notes: Optional[str] = Field(None, max_length=500)


def _to_dict(p: PortfolioPosition) -> dict:
    return {
        "company_id": p.company_id,
        "shares": float(p.shares),
        "cost_basis": float(p.cost_basis),
        "current_price": float(p.current_price) if p.current_price else None,
        "notes": p.notes,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


@router.get("/positions", response_model=StandardResponse)
def list_positions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """列出目前使用者的投資組合部位"""
    positions = (
        db.query(PortfolioPosition)
        .filter(PortfolioPosition.user_id == current_user.user_id)
        .order_by(PortfolioPosition.company_id)
        .all()
    )
    return StandardResponse(
        success=True,
        data={"positions": [_to_dict(p) for p in positions]},
    )


@router.post("/positions", response_model=StandardResponse)
def upsert_position(
    req: PositionInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """新增或更新投資組合部位"""
    if not db.query(Company).filter(Company.company_id == req.company_id).first():
        raise HTTPException(status_code=404, detail=f"找不到公司 {req.company_id}")

    pos = (
        db.query(PortfolioPosition)
        .filter(
            PortfolioPosition.user_id == current_user.user_id,
            PortfolioPosition.company_id == req.company_id,
        )
        .first()
    )
    if pos is None:
        pos = PortfolioPosition(
            user_id=current_user.user_id,
            company_id=req.company_id,
            shares=req.shares,
            cost_basis=req.cost_basis,
            current_price=req.current_price,
            notes=req.notes,
        )
        db.add(pos)
    else:
        pos.shares = req.shares
        pos.cost_basis = req.cost_basis
        pos.current_price = req.current_price
        pos.notes = req.notes

    db.commit()
    db.refresh(pos)
    return StandardResponse(success=True, data=_to_dict(pos), message="部位已儲存")


@router.delete("/positions/{company_id}", response_model=StandardResponse)
def delete_position(
    company_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """刪除投資組合部位"""
    pos = (
        db.query(PortfolioPosition)
        .filter(
            PortfolioPosition.user_id == current_user.user_id,
            PortfolioPosition.company_id == company_id,
        )
        .first()
    )
    if pos is None:
        raise HTTPException(status_code=404, detail=f"找不到部位 {company_id}")

    db.delete(pos)
    db.commit()
    return StandardResponse(success=True, message="部位已刪除")


@router.get("/summary", response_model=StandardResponse)
def summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """投資組合總覽（成本/市值/損益 + 最新 ROE/PE）"""
    rows = db.execute(
        text(
            """
            SELECT p.company_id, c.company_name, p.shares, p.cost_basis, p.current_price,
                   fr.roe, fr.pe_ratio
            FROM portfolio_positions p
            JOIN companies c ON c.company_id = p.company_id
            LEFT JOIN LATERAL (
                SELECT roe, pe_ratio FROM financial_ratios
                WHERE company_id = p.company_id
                ORDER BY year_quarter DESC LIMIT 1
            ) fr ON true
            WHERE p.user_id = :uid
            ORDER BY p.company_id
            """
        ),
        {"uid": current_user.user_id},
    ).mappings().all()

    positions = []
    total_cost = 0.0
    total_value = 0.0
    for r in rows:
        shares = float(r["shares"])
        cost_basis = float(r["cost_basis"])
        cost = shares * cost_basis
        price = float(r["current_price"]) if r["current_price"] else None
        value = shares * price if price else cost
        total_cost += cost
        total_value += value
        positions.append(
            {
                "company_id": r["company_id"],
                "company_name": r["company_name"],
                "shares": shares,
                "cost_basis": cost_basis,
                "current_price": price,
                "market_value": round(value, 2),
                "pnl": round(value - cost, 2),
                "pnl_pct": round((value - cost) / cost * 100, 2) if cost else 0.0,
                "roe": float(r["roe"]) if r["roe"] is not None else None,
                "pe_ratio": float(r["pe_ratio"]) if r["pe_ratio"] is not None else None,
            }
        )

    pnl = total_value - total_cost
    return StandardResponse(
        success=True,
        data={
            "positions": positions,
            "total_cost": round(total_cost, 2),
            "total_value": round(total_value, 2),
            "total_pnl": round(pnl, 2),
            "total_pnl_pct": round(pnl / total_cost * 100, 2) if total_cost else 0.0,
        },
    )
